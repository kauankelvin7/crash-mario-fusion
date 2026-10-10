using System;
using Silk.NET.OpenGL;

namespace RecompOne.Runtime.Host.Window;

internal sealed unsafe class MarioGpuState : IDisposable
{
    internal static readonly EnableCap[] Disabled = [EnableCap.Blend, EnableCap.CullFace,
        EnableCap.ScissorTest, EnableCap.StencilTest, EnableCap.RasterizerDiscard,
        EnableCap.FramebufferSrgb, EnableCap.ColorLogicOp, EnableCap.PolygonOffsetFill,
        EnableCap.SampleAlphaToCoverage, EnableCap.SampleAlphaToOne,
        EnableCap.SampleCoverage, EnableCap.SampleMask, EnableCap.DepthClamp, EnableCap.Dither];
    private readonly GL gl;
    private readonly bool[] enabled;
    internal readonly bool[] ClipEnabled;
    private readonly int drawFbo, readFbo, renderbuffer, program, vao, buffer, pbo;
    private readonly int activeTexture, texture, sampler, depthFunction, polygonMode;
    private readonly bool depthTest, depthMask;
    private readonly int[] viewport = new int[4], colorMask = new int[4];
    private readonly double[] depthRange = new double[2];

    internal MarioGpuState(GL gl)
    {
        this.gl = gl;
        drawFbo = gl.GetInteger(GetPName.DrawFramebufferBinding);
        readFbo = gl.GetInteger(GetPName.ReadFramebufferBinding);
        renderbuffer = gl.GetInteger(GetPName.RenderbufferBinding);
        program = gl.GetInteger(GetPName.CurrentProgram);
        vao = gl.GetInteger(GetPName.VertexArrayBinding);
        buffer = gl.GetInteger(GetPName.ArrayBufferBinding);
        pbo = gl.GetInteger(GetPName.PixelUnpackBufferBinding);
        activeTexture = gl.GetInteger(GetPName.ActiveTexture);
        gl.ActiveTexture(TextureUnit.Texture0);
        try
        {
            texture = gl.GetInteger(GetPName.TextureBinding2D);
            sampler = gl.GetInteger(GetPName.SamplerBinding);
        }
        finally { gl.ActiveTexture((TextureUnit)activeTexture); }
        depthFunction = gl.GetInteger(GetPName.DepthFunc);
        depthTest = gl.IsEnabled(EnableCap.DepthTest);
        depthMask = gl.GetInteger(GetPName.DepthWritemask) != 0;
        int* modes = stackalloc int[2];
        gl.GetInteger(GetPName.PolygonMode, modes);
        polygonMode = modes[0];
        fixed (int* values = viewport) gl.GetInteger(GetPName.Viewport, values);
        fixed (int* values = colorMask) gl.GetInteger(GetPName.ColorWritemask, values);
        fixed (double* values = depthRange) gl.GetDouble(GetPName.DepthRange, values);
        enabled = new bool[Disabled.Length];
        for (int index = 0; index < enabled.Length; index++) enabled[index] = gl.IsEnabled(Disabled[index]);
        ClipEnabled = new bool[gl.GetInteger(GetPName.MaxClipDistances)];
        for (int index = 0; index < ClipEnabled.Length; index++)
            ClipEnabled[index] = gl.IsEnabled((EnableCap)((int)EnableCap.ClipDistance0 + index));
    }
    public void Dispose()
    {
        gl.BindFramebuffer(FramebufferTarget.DrawFramebuffer, (uint)drawFbo);
        gl.BindFramebuffer(FramebufferTarget.ReadFramebuffer, (uint)readFbo);
        gl.BindRenderbuffer(RenderbufferTarget.Renderbuffer, (uint)renderbuffer);
        gl.UseProgram((uint)program);
        gl.BindVertexArray((uint)vao);
        gl.BindBuffer(BufferTargetARB.ArrayBuffer, (uint)buffer);
        gl.BindBuffer(BufferTargetARB.PixelUnpackBuffer, (uint)pbo);
        gl.ActiveTexture(TextureUnit.Texture0);
        gl.BindTexture(TextureTarget.Texture2D, (uint)texture);
        gl.BindSampler(0, (uint)sampler);
        gl.ActiveTexture((TextureUnit)activeTexture);
        gl.Viewport(viewport[0], viewport[1], (uint)viewport[2], (uint)viewport[3]);
        gl.ColorMask(colorMask[0] != 0, colorMask[1] != 0, colorMask[2] != 0, colorMask[3] != 0);
        gl.DepthMask(depthMask);
        gl.DepthFunc((DepthFunction)depthFunction);
        gl.DepthRange(depthRange[0], depthRange[1]);
        gl.PolygonMode(TriangleFace.FrontAndBack, (PolygonMode)polygonMode);
        Set(EnableCap.DepthTest, depthTest);
        for (int index = 0; index < enabled.Length; index++) Set(Disabled[index], enabled[index]);
        for (int index = 0; index < ClipEnabled.Length; index++)
            Set((EnableCap)((int)EnableCap.ClipDistance0 + index), ClipEnabled[index]);
    }

    private void Set(EnableCap capability, bool value)
    {
        if (value) gl.Enable(capability); else gl.Disable(capability);
    }
}
