using RecompOne.Runtime.Host.Window;
using Silk.NET.Maths;
using Silk.NET.OpenGL;
using Silk.NET.Windowing;

internal static partial class Program
{
    private static unsafe byte[] Pixel(GL gl, nint texture, int xpos, int ypos)
    {
        uint readback = gl.GenFramebuffer();
        int prior = gl.GetInteger(GetPName.ReadFramebufferBinding);
        try
        {
            gl.BindFramebuffer(FramebufferTarget.ReadFramebuffer, readback);
            gl.FramebufferTexture2D(FramebufferTarget.ReadFramebuffer, FramebufferAttachment.ColorAttachment0,
                TextureTarget.Texture2D, (uint)texture, 0);
            gl.ReadBuffer(ReadBufferMode.ColorAttachment0);
            byte[] pixel = new byte[4];
            fixed (byte* pointer = pixel)
                gl.ReadPixels(xpos, ypos, 1, 1, PixelFormat.Rgba, PixelType.UnsignedByte, pointer);
            return pixel;
        }
        finally
        {
            gl.BindFramebuffer(FramebufferTarget.ReadFramebuffer, (uint)prior);
            gl.DeleteFramebuffer(readback);
        }
    }

    private static void RunGpu()
    {
        var options = WindowOptions.Default;
        options.IsVisible = false;
        options.Size = new Vector2D<int>(64, 64);
        options.API = new GraphicsAPI(ContextAPI.OpenGL, ContextProfile.Core,
            ContextFlags.ForwardCompatible, new APIVersion(3, 3));
        using var window = Window.Create(options);
        window.Initialize();
        window.MakeCurrent();
        using var gl = GL.GetApi(window);
        Console.WriteLine("GPU_FIXTURE renderer=" + gl.GetStringS(StringName.Renderer) +
            " version=" + gl.GetStringS(StringName.Version));
        Environment.SetEnvironmentVariable("CM64_GPU_SELF_DEPTH", "1");
        OriginalMarioGpu.BeginFrame(gl);
        byte[] atlas = Enumerable.Repeat((byte)255, OriginalMarioAtlas.ByteCount).ToArray();
        OriginalMarioAtlas.QueueAtlas(atlas);
        OriginalMarioAtlas.RenderTick(gl);
        try { CheckGpu(gl); }
        finally
        {
            OriginalMarioGpu.Shutdown(gl);
            OriginalMarioAtlas.Shutdown(gl);
            Environment.SetEnvironmentVariable("CM64_GPU_SELF_DEPTH", null);
        }
    }

    private static void CheckUvAndLifetime(GL gl, float[] clip, float[] weights)
    {
        byte[] gradient = new byte[OriginalMarioAtlas.ByteCount];
        for (int ypos = 0; ypos < OriginalMarioAtlas.Height; ypos++)
            for (int xpos = 0; xpos < OriginalMarioAtlas.Width; xpos++)
            {
                int offset = (ypos * OriginalMarioAtlas.Width + xpos) * 4;
                gradient[offset] = (byte)Math.Round(xpos * 255d / (OriginalMarioAtlas.Width - 1));
                gradient[offset + 1] = (byte)Math.Round(ypos * 255d / (OriginalMarioAtlas.Height - 1));
                gradient[offset + 2] = gradient[offset + 3] = 255;
            }
        OriginalMarioAtlas.QueueAtlas(gradient);
        Array.Clear(gradient);
        OriginalMarioAtlas.RenderTick(gl);
        float[] uv = [.1f,.1f, .9f,.1f, .1f,.9f];
        var frame = new OriginalMarioClipFrame(clip, uv, Enumerable.Repeat(1f, 9).ToArray(), 1, 4);
        Check(OriginalMarioGpu.TryRender(frame, 64, 64, out var target), "textured native-UV fixture");
        var pixel = Pixel(gl, target, 16, 16);
        int texelX = (int)((.1f + .8f * weights[1]) * OriginalMarioAtlas.Width);
        int texelY = (int)((.1f + .8f * weights[2]) * OriginalMarioAtlas.Height);
        Check(Math.Abs(pixel[0] - Math.Round(texelX * 255d / 703)) <= 1,
            "perspective-correct UV U, independent of screen-linear interpolation");
        Check(Math.Abs(pixel[1] - Math.Round(texelY * 255d / 63)) <= 1,
            "perspective-correct UV V and copied atlas bytes");
        OriginalMarioAtlas.ReleaseAtlas();
        OriginalMarioAtlas.RenderTick(gl);
        Check(!OriginalMarioGpu.TryRender(frame, 64, 64, out var released) && released == 0,
            "missing/released atlas returns fallback, not stale texture");
        byte[] green = new byte[OriginalMarioAtlas.ByteCount];
        for (int offset = 0; offset < green.Length; offset += 4)
            green[offset + 1] = green[offset + 3] = 255;
        OriginalMarioAtlas.QueueAtlas(green);
        OriginalMarioAtlas.RenderTick(gl);
        Check(OriginalMarioGpu.TryRender(frame, 96, 96, out var resized) && resized == target,
            "resize retains target lifetime instead of deleting externally referenced texture");
        var reloaded = Pixel(gl, resized, 24, 24);
        Check(reloaded[0] == 0 && reloaded[1] == 255 && reloaded[2] == 0,
            "atlas reload sampled from current original host-owned texture");
        Check(OriginalMarioAtlas.UploadCount == 3, "only render owner uploads/releases atlas");
    }

    private static void CheckGpu(GL gl)
    {
        Check(gl.GetError() == GLEnum.NoError, "fixture context/atlas initialization");
        float[] first = [-1,-1,-.6f,1, 1,-1,.6f,1, -1,1,0,1];
        float[] second = [-1,-1,0,1, 1,-1,0,1, -1,1,0,1];
        float[] red = [1,0,0, 1,0,0, 1,0,0];
        float[] blue = [0,0,1, 0,0,1, 0,0,1];
        float[] sentinel = Enumerable.Repeat(1f, 12).ToArray();
        foreach (bool reversed in new[] { false, true })
        {
            var crossing = new OriginalMarioClipFrame(
                reversed ? second.Concat(first).ToArray() : first.Concat(second).ToArray(), sentinel,
                reversed ? blue.Concat(red).ToArray() : red.Concat(blue).ToArray(), 2, reversed ? 2 : 1);
            Check(OriginalMarioGpu.TryRender(crossing, 64, 64, out var target), "GPU overlap render");
            var left = Pixel(gl, target, 8, 8);
            var right = Pixel(gl, target, 48, 8);
            Check(left[0] == 255 && left[2] == 0 && right[0] == 0 && right[2] == 255,
                "crossing self-depth varies per fragment, independent of triangle order: left=" +
                string.Join(',', left) + " right=" + string.Join(',', right) + " error=" + gl.GetError());
        }
        float[] perspectiveClip = [-1,-1,0,1, 2,-2,0,2, -4,4,0,4];
        float[] vertexColor = [1,0,0, 0,1,0, 0,0,1];
        var perspective = new OriginalMarioClipFrame(perspectiveClip, sentinel.Take(6).ToArray(),
            vertexColor, 1, 3);
        Check(OriginalMarioGpu.TryRender(perspective, 64, 64, out var colorTarget), "GPU perspective render");
        float weightB = 16.5f / 64, weightC = weightB, weightA = 1 - weightB - weightC;
        float denominator = weightA + weightB / 2 + weightC / 4;
        float[] expected = [weightA / denominator, weightB / 2 / denominator, weightC / 4 / denominator];
        var pixel = Pixel(gl, colorTarget, 16, 16);
        for (int component = 0; component < 3; component++)
            Check(Math.Abs(pixel[component] / 255f - expected[component]) < .006f,
                "perspective-correct original per-vertex color component " + component);
        Check(pixel[3] == 255, "untextured colored face retains opacity");
        CheckUvAndLifetime(gl, perspectiveClip, expected);
        CheckStateAndFailure(gl, perspective);
    }
}
