// .NET 10 cross-language ABI smoke: libsm64 original physics on authored test floor.
// Real licensed ROM stays in private memory, no asset/capture export.
using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using CrashMarioFusion.Embedded;

public static unsafe class Probe {
    private const string PinnedRomSha1 = "9BEF1128717F958171A4AFAC3ED78EE2BB4E86CE";
    public static int Main(string[] args) {
        MarioNative.AssertAbi();
        Console.WriteLine("CSHARP_NATIVE_ABI_PASS surface=44 inputs=20 state=60 geometry=40");
        if (args.Length==1 && args[0]=="--abi-only") return 0;
        if(args.Length!=1 || !File.Exists(args[0])) {
            Console.Error.WriteLine("ROM_ARG_REQUIRED: owned Mario US ROM local path");
            return 2;
        }
        var rom=File.ReadAllBytes(args[0]);
        if (rom.Length!=MarioNative.RomBytes ||
            Convert.ToHexString(SHA1.HashData(rom))!=PinnedRomSha1) {
            Console.Error.WriteLine("Invalid original US Mario ROM hash/size");
            return 2;
        }
        var dll=Path.Combine(AppContext.BaseDirectory,"sm64.dll");
        if(!File.Exists(dll)) throw new FileNotFoundException("Private native libsm64 DLL missing");
        // Resolver uses the exact locally deployed native library, not PATH search.
        NativeLibrary.SetDllImportResolver(typeof(MarioNative).Assembly,
            (name, assembly, path) => name == "sm64.dll" ? NativeLibrary.Load(dll) : IntPtr.Zero);
        byte* texture=(byte*)NativeMemory.AllocZeroed(MarioNative.TextureBytes);
        float* positions=(float*)NativeMemory.AllocZeroed(9216,4);
        float* normals=(float*)NativeMemory.AllocZeroed(9216,4);
        float* colors=(float*)NativeMemory.AllocZeroed(9216,4);
        float* uv=(float*)NativeMemory.AllocZeroed(6144,4);
        if(texture==null||positions==null||normals==null||colors==null||uv==null)
            throw new OutOfMemoryException();
        int mario=-1; bool started=false;
        try {
            fixed (byte* ownedRom=rom) MarioNative.sm64_global_init(ownedRom,texture);
            started=true;
            MarioSurface* platform=stackalloc MarioSurface[2];
            MarioNative.AddAuthoredFloor(platform);
            MarioNative.sm64_static_surfaces_load(platform,2);
            mario=MarioNative.sm64_mario_create(0,250,0);
            if(mario<0) throw new InvalidOperationException("Mario original actor initialization failed");
            MarioInputs input=new(){CamLookX=1,CamLookZ=0};
            MarioState state=default;
            MarioGeometry mesh=new(){Position=positions,Normal=normals,Color=colors,Uv=uv};
            int geometryFrames=0,motionFrames=0;
            float x0=0,z0=0,x1=0,z1=0,minY=float.PositiveInfinity;
            for(int i=0;i<180;++i) {
                input.StickY=i>=70 && i<155 ? .75f : 0f;
                input.ButtonA=(byte)(i==125?1:0);
                mesh.NumTrianglesUsed=0;
                MarioNative.sm64_mario_tick(mario,&input,&state,&mesh);
                var x=state.Position[0];var y=state.Position[1];var z=state.Position[2];
                if(!float.IsFinite(x)||!float.IsFinite(y)||!float.IsFinite(z)||
                   mesh.NumTrianglesUsed>MarioNative.MaxTriangles)
                    throw new InvalidOperationException("Invalid native Mario physics/renderer output");
                if(i==69){x0=x;z0=z;}
                if(i==179){x1=x;z1=z;}
                minY=MathF.Min(minY,y);
                if(mesh.NumTrianglesUsed>0)geometryFrames++;
                if(MathF.Abs(state.Velocity[0])+MathF.Abs(state.Velocity[2])>.005f)motionFrames++;
            }
            var traveled=MathF.Sqrt((x1-x0)*(x1-x0)+(z1-z0)*(z1-z0));
            Console.WriteLine($"CSHARP_ORIGINAL_MARIO_SOLVER frames=180 mesh_frames={geometryFrames} motion_frames={motionFrames} travel={traveled:F3} minY={minY:F3} shared_crash_collision=false");
            if(geometryFrames<100||motionFrames<20||traveled<2||minY<-500)
                return 1;
            return 0;
        } finally {
            if(mario>=0)MarioNative.sm64_mario_delete(mario);
            if(started)MarioNative.sm64_global_terminate();
            NativeMemory.Free(texture);NativeMemory.Free(positions);NativeMemory.Free(normals);NativeMemory.Free(colors);NativeMemory.Free(uv);
            CryptographicOperations.ZeroMemory(rom);
        }
    }
}
