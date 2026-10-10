// M4.1B2B: read-only native Crash camera source probe.
// Pinned original SCUS-94900 + Crash Launcher 224da775 only.
// PadRead is an UNKNOWN_DIAGNOSTIC sampling phase, not postphysics.
// Reads raw RAM Span; never IMemory.ReadU32 (may cause VBlank side effects).
using System;
using System.Buffers.Binary;
using RecompOne.Runtime.Events;
using RecompOne.Runtime.Hardware;
using RecompOne.Runtime.Catalogs;
using RecompOne.Runtime.Memory;

internal static class CrashCameraProbe
{
    private const uint Base=0x80000000u;
    private const uint Matrix=0x800577E4u;        // original 9 signed 16-bit GTE matrix entries
    private const uint CamTrans=0x80057864u;      // original raw xyz fixed-point camera translation
    private const uint Projection=0x800578D0u;    // original projection scalar
    private const uint CamZone=0x80057914u;       // zone pointer
    private const uint CamPath=0x8005791Cu;       // path pointer
    private const uint CamProgress=0x80057920u;   // path progress
    private const uint Pause=0x80056400u;
    private const uint PauseAlternate=0x8005640Cu;
    private static bool armed;
    private static long startMs,lastMs;
    private static int sequence,epoch,accepted,changed;
    private static uint lastLevel,lastZone,lastPath,lastProgress;
    private static int lastTx,lastTy,lastTz,lastProjection;
    private static readonly short[] previousMatrix = new short[9];
    private static bool hadSample;

    private static bool Fits(uint addr,int bytes) =>
        addr>=Base && addr <= Base+0x200000u-(uint)bytes;
    private static uint U32(ReadOnlySpan<byte> ram,uint addr) =>
        BinaryPrimitives.ReadUInt32LittleEndian(ram.Slice(checked((int)(addr-Base)),4));
    private static short S16(ReadOnlySpan<byte> ram,uint addr) =>
        BinaryPrimitives.ReadInt16LittleEndian(ram.Slice(checked((int)(addr-Base)),2));

    public static void Start()
    {
        if(armed) return;
        armed=true;startMs=lastMs=Environment.TickCount64;
        sequence=epoch=accepted=changed=0;hadSample=false;
        Event.AddListener<PadReadEvent>(OnPad);
        Console.WriteLine("[cm64-camera] SOURCE_PROBE_ARMED callback=PadRead phase=UNKNOWN_DIAGNOSTIC actual_crash_camera_calibration=false");
    }
    public static void Stop()
    {
        if(!armed) return;
        Event.RemoveListener<PadReadEvent>(OnPad);armed=false;
        Console.WriteLine("[cm64-camera] SOURCE_PROBE_STOP samples="+accepted+
           " changed="+changed+" epoch="+epoch+" calibration_ready=false phase=UNKNOWN_DIAGNOSTIC");
    }
    private static void OnPad(PadReadEvent e)
    {
        if(!armed || e.Port!=0) return;
        long now=Environment.TickCount64;
        if(now-startMs>90000 || accepted>=48){Stop();return;}
        if(now-lastMs<900)return;
        long previousMs=lastMs;
        lastMs=now;
        try
        {
            if(e.Memory is not PSMemory m || m.Ram.Length!=0x200000 ||
                !Fits(Matrix,18) || !Fits(CamTrans,12) ||
                !Fits(Projection,4) || !Fits(CamZone,4) ||
                !Fits(CamPath,4) || !Fits(CamProgress,4) ||
                !Fits(Catalog.LevelIdAddr,4) || !Fits(Pause,4) ||
                !Fits(PauseAlternate,4)) { hadSample=false;return; }
            ReadOnlySpan<byte> ram=m.Ram;
            uint level=U32(ram,Catalog.LevelIdAddr);
            if(!Catalog.Levels.TryGet(level,out var info) || info.Kind!=LevelKind.Gameplay ||
                U32(ram,Pause)!=0 || U32(ram,PauseAlternate)!=0 ||
                (e.Buttons & Controller.Start)==0)
            { hadSample=false;return; }
            int proj=(int)U32(ram,Projection);
            if(proj<=0 || proj>4096){hadSample=false;return;}
            uint zone=U32(ram,CamZone),path=U32(ram,CamPath),progress=U32(ram,CamProgress);
            if(!Fits(zone,4) || !Fits(path,4)){hadSample=false;return;}
            int tx=unchecked((int)U32(ram,CamTrans));
            int ty=unchecked((int)U32(ram,CamTrans+4u));
            int tz=unchecked((int)U32(ram,CamTrans+8u));
            var matrix=new short[9];
            bool nonzero=false;
            for(int i=0;i<9;++i){matrix[i]=S16(ram,Matrix+(uint)i*2u);nonzero |= matrix[i]!=0;}
            if(!nonzero){hadSample=false;return;}
            if(!hadSample || level!=lastLevel || zone!=lastZone || path!=lastPath || now-previousMs>3000)
                ++epoch;
            bool varied=!hadSample || proj!=lastProjection || tx!=lastTx || ty!=lastTy ||
                tz!=lastTz || progress!=lastProgress;
            for(int i=0;i<9;i++)varied |= matrix[i]!=previousMatrix[i];
            if(varied && hadSample)changed++;
            hadSample=true;lastLevel=level;lastZone=zone;lastPath=path;lastProgress=progress;
            lastProjection=proj;lastTx=tx;lastTy=ty;lastTz=tz;
            Array.Copy(matrix,previousMatrix,9);
            accepted++;
            // Values explicitly RAW as read from the original guest. No projection
            // to Mario, never label this callback postphysics.
            Console.WriteLine("[cm64-camera] RAW_SAMPLE phase=PAD_UNKNOWN level="+level+
                " seq="+(++sequence)+" epoch="+epoch+" projection="+proj+
                " zone=0x"+zone.ToString("X8")+" path=0x"+path.ToString("X8")+
                " progress="+progress+" tx="+tx+" ty="+ty+" tz="+tz+
                " m="+string.Join(",",matrix)+" changed="+(varied?"1":"0")+
                " safe_for_shared_depth=false");
        }
        catch(Exception ex)
        {
            Console.Error.WriteLine("[cm64-camera] SOURCE_PROBE_DISABLED "+ex.GetType().Name);
            Stop(); // never escape into original Crash input bus
        }
    }
}
