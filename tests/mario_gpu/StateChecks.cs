using System.Reflection;
using RecompOne.Runtime.Host.Window;
using Silk.NET.OpenGL;

internal static partial class Program
{
    private static uint Resource(string name) => (uint)typeof(OriginalMarioGpu).GetField(
        name, BindingFlags.Static | BindingFlags.NonPublic)!.GetValue(null)!;

    private static unsafe string Capture(GL gl)
    {
        var values = new List<string>();
        foreach (var state in new[] { GetPName.DrawFramebufferBinding, GetPName.ReadFramebufferBinding,
            GetPName.RenderbufferBinding, GetPName.CurrentProgram, GetPName.VertexArrayBinding,
            GetPName.ArrayBufferBinding, GetPName.PixelUnpackBufferBinding, GetPName.ActiveTexture,
            GetPName.DepthFunc, GetPName.DepthWritemask }) values.Add(gl.GetInteger(state).ToString());
        int active = gl.GetInteger(GetPName.ActiveTexture);
        gl.ActiveTexture(TextureUnit.Texture0);
        values.Add(gl.GetInteger(GetPName.TextureBinding2D).ToString());
        values.Add(gl.GetInteger(GetPName.SamplerBinding).ToString());
        gl.ActiveTexture((TextureUnit)active);
        values.Add(gl.GetInteger(GetPName.TextureBinding2D).ToString());
        foreach (var state in new[] { GetPName.Viewport, GetPName.ColorWritemask, GetPName.PolygonMode })
        {
            int count = state == GetPName.PolygonMode ? 2 : 4;
            int[] integers = new int[count];
            fixed (int* pointer = integers) gl.GetInteger(state, pointer);
            values.Add(string.Join(',', integers));
        }
        double[] range = new double[2];
        fixed (double* pointer = range) gl.GetDouble(GetPName.DepthRange, pointer);
        values.Add(string.Join(',', range));
        foreach (var capability in MarioGpuState.Disabled.Append(EnableCap.DepthTest))
            values.Add(gl.IsEnabled(capability).ToString());
        for (int index = 0; index < gl.GetInteger(GetPName.MaxClipDistances); index++)
            values.Add(gl.IsEnabled((EnableCap)((int)EnableCap.ClipDistance0 + index)).ToString());
        return string.Join('|', values);
    }

    private static void CheckStateAndFailure(GL gl, OriginalMarioClipFrame frame)
    {
        uint hostVao = gl.GenVertexArray(), hostBuffer = gl.GenBuffer(), hostSampler = gl.GenSampler();
        uint hostDraw = gl.GenFramebuffer(), hostRead = gl.GenFramebuffer(), hostDepth = gl.GenRenderbuffer();
        uint hostTexture0 = gl.GenTexture(), hostTexture3 = gl.GenTexture();
        gl.BindFramebuffer(FramebufferTarget.DrawFramebuffer, hostDraw);
        gl.BindFramebuffer(FramebufferTarget.ReadFramebuffer, hostRead);
        gl.BindRenderbuffer(RenderbufferTarget.Renderbuffer, hostDepth);
        gl.ActiveTexture(TextureUnit.Texture0);
        gl.BindTexture(TextureTarget.Texture2D, hostTexture0);
        gl.BindVertexArray(hostVao);
        gl.BindBuffer(BufferTargetARB.ArrayBuffer, hostBuffer);
        gl.BindBuffer(BufferTargetARB.PixelUnpackBuffer, hostBuffer);
        gl.BindSampler(0, hostSampler);
        gl.ActiveTexture(TextureUnit.Texture3);
        gl.BindTexture(TextureTarget.Texture2D, hostTexture3);
        gl.Enable(EnableCap.ScissorTest);
        gl.Enable(EnableCap.Blend);
        gl.Enable(EnableCap.CullFace);
        gl.Enable(EnableCap.ClipDistance0);
        gl.DepthFunc(DepthFunction.Greater);
        gl.DepthMask(false);
        gl.DepthRange(.2, .8);
        gl.ColorMask(false, true, false, true);
        gl.PolygonMode(TriangleFace.FrontAndBack, PolygonMode.Line);
        gl.Viewport(7, 9, 23, 31);
        string before = Capture(gl);
        Check(OriginalMarioGpu.TryRender(frame, 64, 64, out var target), "hostile-state diagnostic render");
        Check(Capture(gl) == before, "success restores host bindings, masks, ranges and capabilities");
        CheckFailure(gl, frame, target, before);
        gl.BindBuffer(BufferTargetARB.PixelUnpackBuffer, 0);
        gl.BindBuffer(BufferTargetARB.ArrayBuffer, 0);
        gl.BindVertexArray(0);
        gl.BindSampler(0, 0);
        gl.DeleteVertexArray(hostVao);
        gl.DeleteBuffer(hostBuffer);
        gl.DeleteSampler(hostSampler);
        gl.BindFramebuffer(FramebufferTarget.DrawFramebuffer, 0);
        gl.BindFramebuffer(FramebufferTarget.ReadFramebuffer, 0);
        gl.BindRenderbuffer(RenderbufferTarget.Renderbuffer, 0);
        gl.DeleteFramebuffer(hostDraw);
        gl.DeleteFramebuffer(hostRead);
        gl.DeleteRenderbuffer(hostDepth);
        gl.DeleteTexture(hostTexture0);
        gl.DeleteTexture(hostTexture3);
    }
    private static void CheckFailure(GL gl, OriginalMarioClipFrame frame, nint target, string before)
    {
        uint framebuffer = Resource("framebuffer");
        int previous = gl.GetInteger(GetPName.DrawFramebufferBinding);
        gl.BindFramebuffer(FramebufferTarget.DrawFramebuffer, framebuffer);
        gl.FramebufferTexture2D(FramebufferTarget.DrawFramebuffer, FramebufferAttachment.ColorAttachment0,
            TextureTarget.Texture2D, 0, 0);
        gl.FramebufferRenderbuffer(FramebufferTarget.DrawFramebuffer, FramebufferAttachment.DepthAttachment,
            RenderbufferTarget.Renderbuffer, 0);
        gl.BindFramebuffer(FramebufferTarget.DrawFramebuffer, (uint)previous);
        Check(!OriginalMarioGpu.TryRender(frame, 64, 64, out var failed) && failed == 0,
            "incomplete FBO fails closed without stale output");
        Check(Capture(gl) == before && OriginalMarioGpu.LastTick == 0,
            "failure restores host state and clears completed frame identity");
        bool rejected = false, cleanupRejected = false;
        var wrongThread = new Thread(() =>
        {
            try { OriginalMarioGpu.TryRender(frame, 64, 64, out _); }
            catch (InvalidOperationException) { rejected = true; }
            try { OriginalMarioGpu.Shutdown(gl); }
            catch (InvalidOperationException) { cleanupRejected = true; }
        });
        wrongThread.Start(); wrongThread.Join();
        Check(rejected && cleanupRejected && Capture(gl) == before,
            "wrong render/cleanup thread rejected before any GL operation");
        string[] names = ["program", "vao", "vbo", "framebuffer", "colorTexture", "depthBuffer"];
        uint[] resources = names.Select(Resource).ToArray();
        OriginalMarioGpu.Shutdown(gl);
        Check(!gl.IsProgram(resources[0]) && !gl.IsVertexArray(resources[1]) && !gl.IsBuffer(resources[2]) &&
            !gl.IsFramebuffer(resources[3]) && !gl.IsTexture(resources[4]) && !gl.IsRenderbuffer(resources[5]),
            "owner shutdown deletes every renderer resource");
        OriginalMarioGpu.Shutdown(gl);
        Check(names.All(name => Resource(name) == 0), "shutdown is idempotent and resets all handles");
        OriginalMarioGpu.BeginFrame(gl);
        Check(OriginalMarioGpu.TryRender(frame, 64, 64, out var restarted) && restarted != 0,
            "new host session reconstructs resources");
        Check(gl.GetError() == GLEnum.NoError, "all synthetic GPU operations leave no GL error");
    }
}
