using System;
using Silk.NET.OpenGL;

namespace RecompOne.Runtime.Host.Window;

public static unsafe class OriginalMarioGpu
{
    internal const string VertexSource = """
        #version 330 core
        layout(location=0) in vec4 clip;
        layout(location=1) in vec2 nativeUv;
        layout(location=2) in vec3 nativeColor;
        layout(location=3) in float nativeTextured;
        smooth out vec2 uv;
        smooth out vec3 color;
        flat out float textured;
        void main() {
            gl_Position = clip;
            uv = nativeUv;
            color = nativeColor;
            textured = nativeTextured;
        }
        """;
    internal const string FragmentSource = """
        #version 330 core
        uniform sampler2D atlas;
        smooth in vec2 uv;
        smooth in vec3 color;
        flat in float textured;
        out vec4 pixel;
        void main() {
            pixel = vec4(color, 1.0);
            if (textured > 0.5) pixel *= texture(atlas, uv);
            if (pixel.a == 0.0) discard;
        }
        """;

    private static GL? context;
    private static int owner;
    private static uint program, vao, vbo, framebuffer, colorTexture, depthBuffer;
    private static int targetWidth, targetHeight;
    public static int LastTick { get; private set; }

    internal static void BeginFrame(GL gl)
    {
        if (context != null && (!ReferenceEquals(context, gl) || owner != Environment.CurrentManagedThreadId))
            throw new InvalidOperationException("Original host GL owner/context changed without shutdown");
        context = gl;
        owner = Environment.CurrentManagedThreadId;
    }

    public static bool TryRender(OriginalMarioClipFrame frame, int width, int height, out nint texture)
    {
        texture = 0;
        if (Environment.GetEnvironmentVariable("CM64_GPU_SELF_DEPTH") != "1") return false;
        GL gl = RequireOwner();
        if (frame == null || width < 1 || height < 1 || width > 2048 || height > 2048)
            throw new ArgumentException("Invalid diagnostic target/frame");
        if (OriginalMarioAtlas.TextureId == 0) return false;
        using var saved = new MarioGpuState(gl);
        try
        {
            gl.ActiveTexture(TextureUnit.Texture0);
            EnsureResources(gl);
            gl.BindFramebuffer(FramebufferTarget.Framebuffer, framebuffer);
            gl.ActiveTexture(TextureUnit.Texture0);
            gl.BindTexture(TextureTarget.Texture2D, colorTexture);
            gl.BindBuffer(BufferTargetARB.PixelUnpackBuffer, 0);
            if (targetWidth != width || targetHeight != height)
            {
                gl.TexImage2D(TextureTarget.Texture2D, 0, (int)InternalFormat.Rgba8,
                    (uint)width, (uint)height, 0, PixelFormat.Rgba, PixelType.UnsignedByte, null);
                gl.BindRenderbuffer(RenderbufferTarget.Renderbuffer, depthBuffer);
                gl.RenderbufferStorage(RenderbufferTarget.Renderbuffer, InternalFormat.DepthComponent24,
                    (uint)width, (uint)height);
                targetWidth = width;
                targetHeight = height;
            }
            if (gl.CheckFramebufferStatus(FramebufferTarget.Framebuffer) != GLEnum.FramebufferComplete)
                throw new InvalidOperationException("Incomplete Mario-only framebuffer");
            DrawFrame(gl, saved, frame, width, height);
            LastTick = frame.Tick;
            texture = (nint)colorTexture;
            return true;
        }
        catch (Exception error)
        {
            targetWidth = targetHeight = LastTick = 0;
            Console.Error.WriteLine("[cm64-gpu] diagnostic unavailable: " + error.GetType().Name);
            return false;
        }
    }

    private static void DrawFrame(GL gl, MarioGpuState saved, OriginalMarioClipFrame frame, int width, int height)
    {
        foreach (var capability in MarioGpuState.Disabled) gl.Disable(capability);
        for (int index = 0; index < saved.ClipEnabled.Length; index++)
            gl.Disable((EnableCap)((int)EnableCap.ClipDistance0 + index));
        gl.Enable(EnableCap.DepthTest);
        gl.DepthFunc(DepthFunction.Less);
        gl.DepthMask(true);
        gl.DepthRange(0, 1);
        gl.ColorMask(true, true, true, true);
        gl.PolygonMode(TriangleFace.FrontAndBack, PolygonMode.Fill);
        gl.Viewport(0, 0, (uint)width, (uint)height);
        float* clearColor = stackalloc float[4] { 0, 0, 0, 0 };
        float clearDepth = 1;
        gl.ClearBuffer(BufferKind.Color, 0, clearColor);
        gl.ClearBuffer(BufferKind.Depth, 0, &clearDepth);
        gl.UseProgram(program);
        gl.BindVertexArray(vao);
        gl.BindBuffer(BufferTargetARB.ArrayBuffer, vbo);
        fixed (float* vertices = frame.Vertices)
            gl.BufferData(BufferTargetARB.ArrayBuffer, (nuint)(frame.Vertices.Length * sizeof(float)),
                vertices, BufferUsageARB.StreamDraw);
        gl.BindTexture(TextureTarget.Texture2D, (uint)OriginalMarioAtlas.TextureId);
        gl.BindSampler(0, 0);
        gl.DrawArrays(PrimitiveType.Triangles, 0, (uint)(frame.Triangles * 3));
    }

    private static uint Shader(GL gl, ShaderType type, string source)
    {
        uint shader = gl.CreateShader(type);
        try
        {
            gl.ShaderSource(shader, source);
            gl.CompileShader(shader);
            gl.GetShader(shader, ShaderParameterName.CompileStatus, out int success);
            if (success == 0) throw new InvalidOperationException(gl.GetShaderInfoLog(shader));
            return shader;
        }
        catch { gl.DeleteShader(shader); throw; }
    }

    private static void EnsureResources(GL gl)
    {
        if (program != 0) return;
        uint vertex = 0, fragment = 0;
        try
        {
            vertex = Shader(gl, ShaderType.VertexShader, VertexSource);
            fragment = Shader(gl, ShaderType.FragmentShader, FragmentSource);
            program = gl.CreateProgram();
            gl.AttachShader(program, vertex);
            gl.AttachShader(program, fragment);
            gl.LinkProgram(program);
            gl.GetProgram(program, ProgramPropertyARB.LinkStatus, out int success);
            if (success == 0) throw new InvalidOperationException(gl.GetProgramInfoLog(program));
            gl.UseProgram(program);
            gl.Uniform1(gl.GetUniformLocation(program, "atlas"), 0);
            vao = gl.GenVertexArray();
            vbo = gl.GenBuffer();
            gl.BindVertexArray(vao);
            gl.BindBuffer(BufferTargetARB.ArrayBuffer, vbo);
            uint[] sizes = [4, 2, 3, 1];
            uint offset = 0;
            for (uint attribute = 0; attribute < sizes.Length; attribute++)
            {
                gl.EnableVertexAttribArray(attribute);
                gl.VertexAttribPointer(attribute, (int)sizes[attribute], VertexAttribPointerType.Float,
                    false, 10 * sizeof(float), (void*)(offset * sizeof(float)));
                offset += sizes[attribute];
            }
            framebuffer = gl.GenFramebuffer();
            colorTexture = gl.GenTexture();
            depthBuffer = gl.GenRenderbuffer();
            if (vao == 0 || vbo == 0 || framebuffer == 0 || colorTexture == 0 || depthBuffer == 0)
                throw new InvalidOperationException("GPU allocation failed");
            gl.BindTexture(TextureTarget.Texture2D, colorTexture);
            gl.TexParameter(TextureTarget.Texture2D, TextureParameterName.TextureMinFilter, (int)GLEnum.Nearest);
            gl.TexParameter(TextureTarget.Texture2D, TextureParameterName.TextureMagFilter, (int)GLEnum.Nearest);
            gl.TexParameter(TextureTarget.Texture2D, TextureParameterName.TextureWrapS, (int)GLEnum.ClampToEdge);
            gl.TexParameter(TextureTarget.Texture2D, TextureParameterName.TextureWrapT, (int)GLEnum.ClampToEdge);
            gl.BindFramebuffer(FramebufferTarget.Framebuffer, framebuffer);
            gl.FramebufferTexture2D(FramebufferTarget.Framebuffer, FramebufferAttachment.ColorAttachment0,
                TextureTarget.Texture2D, colorTexture, 0);
            gl.BindRenderbuffer(RenderbufferTarget.Renderbuffer, depthBuffer);
            gl.FramebufferRenderbuffer(FramebufferTarget.Framebuffer, FramebufferAttachment.DepthAttachment,
                RenderbufferTarget.Renderbuffer, depthBuffer);
        }
        catch { DeleteResources(gl); throw; }
        finally
        {
            if (vertex != 0) gl.DeleteShader(vertex);
            if (fragment != 0) gl.DeleteShader(fragment);
        }
    }

    private static void DeleteResources(GL gl)
    {
        if (program != 0) gl.DeleteProgram(program);
        if (vao != 0) gl.DeleteVertexArray(vao);
        if (vbo != 0) gl.DeleteBuffer(vbo);
        if (framebuffer != 0) gl.DeleteFramebuffer(framebuffer);
        if (colorTexture != 0) gl.DeleteTexture(colorTexture);
        if (depthBuffer != 0) gl.DeleteRenderbuffer(depthBuffer);
        program = vao = vbo = framebuffer = colorTexture = depthBuffer = 0;
        targetWidth = targetHeight = LastTick = 0;
    }

    internal static void Shutdown(GL? gl)
    {
        if (context == null) return;
        if (!ReferenceEquals(gl, context)) throw new InvalidOperationException("Wrong shutdown context");
        DeleteResources(RequireOwner());
        context = null;
        owner = 0;
    }

    private static GL RequireOwner()
    {
        if (context == null || owner != Environment.CurrentManagedThreadId)
            throw new InvalidOperationException("Mario GPU calls require original OutputPanel GL owner");
        return context;
    }
}
