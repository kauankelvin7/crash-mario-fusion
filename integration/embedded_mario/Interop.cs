// Exact pinned libsm64 fd118132 Windows x64 C ABI; no ROM/texture data committed.
using System;
using System.Runtime.InteropServices;

namespace CrashMarioFusion.Embedded;

[StructLayout(LayoutKind.Sequential)]
public unsafe struct MarioSurface {
    public short Type;
    public short Force;
    public ushort Terrain;
    public fixed int Vertices[9];
}
[StructLayout(LayoutKind.Sequential)]
public struct MarioInputs {
    public float CamLookX, CamLookZ, StickX, StickY;
    public byte ButtonA, ButtonB, ButtonZ;
}
[StructLayout(LayoutKind.Sequential)]
public unsafe struct MarioState {
    public fixed float Position[3];
    public fixed float Velocity[3];
    public float FaceAngle, ForwardVelocity;
    public short Health;
    public uint Action;
    public int AnimId;
    public short AnimFrame;
    public uint Flags, ParticleFlags;
    public short InvincTimer;
}
[StructLayout(LayoutKind.Sequential)]
public unsafe struct MarioGeometry {
    public float* Position, Normal, Color, Uv;
    public ushort NumTrianglesUsed;
}
public static unsafe class MarioNative {
    public const int MaxTriangles = 1024;
    public const int TextureBytes = 704 * 64 * 4;
    public const int RomBytes = 8 * 1024 * 1024;
    [DllImport("sm64.dll", CallingConvention = CallingConvention.Cdecl, ExactSpelling=true)]
    public static extern void sm64_global_init(byte* rom, byte* outTexture);
    [DllImport("sm64.dll", CallingConvention = CallingConvention.Cdecl, ExactSpelling=true)]
    public static extern void sm64_global_terminate();
    [DllImport("sm64.dll", CallingConvention = CallingConvention.Cdecl, ExactSpelling=true)]
    public static extern void sm64_static_surfaces_load(MarioSurface* surfaces, uint count);
    [DllImport("sm64.dll", CallingConvention = CallingConvention.Cdecl, ExactSpelling=true)]
    public static extern int sm64_mario_create(float x,float y,float z);
    [DllImport("sm64.dll", CallingConvention = CallingConvention.Cdecl, ExactSpelling=true)]
    public static extern void sm64_mario_tick(int id, MarioInputs* inputs, MarioState* state, MarioGeometry* geometry);
    [DllImport("sm64.dll", CallingConvention = CallingConvention.Cdecl, ExactSpelling=true)]
    public static extern void sm64_mario_delete(int id);

    public static void AssertAbi() {
        if (IntPtr.Size != 8 || sizeof(MarioSurface)!=44 || sizeof(MarioInputs)!=20 ||
            sizeof(MarioState)!=60 || sizeof(MarioGeometry)!=40)
            throw new InvalidOperationException("Native x64 libsm64 ABI layout mismatch");
    }

    public static void AddAuthoredFloor(MarioSurface* triangles) {
        // Counter-clockwise floor from above; authored test geometry, never Crash.
        triangles[0]=default; triangles[1]=default;
        int* a=triangles[0].Vertices;
        a[0]=-1600; a[1]=0; a[2]=-1600;
        a[3]=1600; a[4]=0; a[5]=1600;
        a[6]=1600; a[7]=0; a[8]=-1600;
        int* b=triangles[1].Vertices;
        b[0]=-1600; b[1]=0; b[2]=-1600;
        b[3]=-1600; b[4]=0; b[5]=1600;
        b[6]=1600; b[7]=0; b[8]=1600;
    }
}
