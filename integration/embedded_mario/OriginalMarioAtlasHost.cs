// M4.1B2A generated into a private pinned Crash host checkout only.
// GPU atlas lifetime is owned by the original Crash GL render thread.
// The texture bytes derive privately from the user's local SM64 ROM.
using System;
using System.Threading;
using Silk.NET.OpenGL;

namespace RecompOne.Runtime.Host.Window;

public static unsafe class OriginalMarioAtlas
{
    public const int Width = 704, Height = 64, ByteCount = Width * Height * 4;
    private static readonly object Gate = new();
    private static byte[]? pending;
    private static bool releasePending;
    private static uint textureId;
    private static int uploadCount;

    public static void QueueAtlas(byte[] pixels)
    {
        if (pixels == null || pixels.Length != ByteCount)
            throw new ArgumentException("Expected pinned libsm64 RGBA 704x64 atlas");
        var copy=(byte[])pixels.Clone();
        lock (Gate) { pending=copy; releasePending=true; }
    }
    public static void ReleaseAtlas()
    {
        lock (Gate) { pending=null; releasePending=true; }
    }
    // Called only within OutputPanel.DrawImage with an active original GL context.
    internal static void RenderTick(GL gl)
    {
        byte[]? bytes;
        bool remove;
        lock(Gate)
        {
            bytes=pending;
            pending=null;
            remove=releasePending;
            releasePending=false;
        }
        if(remove && textureId != 0) {
            gl.DeleteTexture(textureId);
            textureId=0;
        }
        if(bytes==null) return;
        int previousBinding=gl.GetInteger(GetPName.TextureBinding2D);
        int previousUnpack=gl.GetInteger(GetPName.UnpackAlignment);
        int previousPbo=gl.GetInteger(GetPName.PixelUnpackBufferBinding);
        uint created=0;
        try
        {
            created=gl.GenTexture();
            if(created==0) throw new InvalidOperationException("OpenGL texture allocation failed");
            gl.BindTexture(TextureTarget.Texture2D, created);
            gl.TexParameter(TextureTarget.Texture2D, TextureParameterName.TextureMinFilter,(int)GLEnum.Nearest);
            gl.TexParameter(TextureTarget.Texture2D, TextureParameterName.TextureMagFilter,(int)GLEnum.Nearest);
            gl.TexParameter(TextureTarget.Texture2D, TextureParameterName.TextureWrapS,(int)GLEnum.ClampToEdge);
            gl.TexParameter(TextureTarget.Texture2D, TextureParameterName.TextureWrapT,(int)GLEnum.ClampToEdge);
            gl.PixelStore(PixelStoreParameter.UnpackAlignment,1);
            gl.BindBuffer(BufferTargetARB.PixelUnpackBuffer,0);
            fixed(byte* pointer=bytes)
                gl.TexImage2D(TextureTarget.Texture2D,0,(int)InternalFormat.Rgba8,
                    Width,Height,0,PixelFormat.Rgba,PixelType.UnsignedByte,pointer);
            textureId=created;
            Interlocked.Increment(ref uploadCount);
            Console.WriteLine("[cm64-atlas] HOST_GL_ATLAS_UPLOADED width=704 height=64 private=true");
        }
        finally
        {
            gl.BindBuffer(BufferTargetARB.PixelUnpackBuffer,(uint)previousPbo);
            gl.PixelStore(PixelStoreParameter.UnpackAlignment,previousUnpack);
            gl.BindTexture(TextureTarget.Texture2D,(uint)previousBinding);
            Array.Clear(bytes);
            if(created!=0 && textureId!=created) gl.DeleteTexture(created);
        }
    }
    public static nint TextureId => (nint)textureId;
    public static int UploadCount => Volatile.Read(ref uploadCount);
    internal static void Shutdown(GL? gl)
    {
        lock(Gate){pending=null;releasePending=false;}
        if(gl!=null && textureId!=0) gl.DeleteTexture(textureId);
        textureId=0;
    }
}
