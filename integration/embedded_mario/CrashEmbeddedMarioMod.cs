// M4 opt-in, read-only-from-Crash hosted Mario native solver diagnostic.
// Crash runtime physics, PadRead, guest RAM, rendering and inputs are untouched.
// VSync is ONLY a host callback; it is NOT certified postphysics.
using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.Json;
using CrashMarioFusion.Embedded;
using RecompOne.Runtime.Events;
using RecompOne.Runtime.Modding;

public sealed unsafe class CrashEmbeddedMarioMod : IMod
{
    const string OwnedMarioHash = "9BEF1128717F958171A4AFAC3ED78EE2BB4E86CE";
    bool enabled, started, halted, inOutput, textured, cameraProbe;
    int marioId = -1, ticks, geometryFrames, movingFrames;
    long lastTickTime, loadedAt;
    string ownedMarioPath = "";
    byte* texture;
    float* meshPositions, meshNormals, meshColors, meshUv;
    MarioState state;
    MarioInputs input;
    MarioGeometry geometry;
    readonly object nativeLock = new();
    bool live;
    int nativeThread, liveEpoch = -1, liveActorEpoch;
    StreamWriter liveTrace;

    public void OnLoad()
    {
        if (Environment.GetEnvironmentVariable("CM64_EMBED_ENABLE") != "1") return;
        MarioNative.AssertAbi();
        ownedMarioPath = Environment.GetEnvironmentVariable("CM64_EMBED_ROM") ?? "";
        if (!File.Exists(ownedMarioPath) ||
            !File.Exists(Path.Combine(AppContext.BaseDirectory, "sm64.dll")))
            throw new InvalidOperationException("Missing private original Mario ROM or local native DLL");
        enabled = true;
        loadedAt = Stopwatch.GetTimestamp();
        inOutput = Environment.GetEnvironmentVariable("CM64_INOUTPUT") == "1";
        textured = inOutput && Environment.GetEnvironmentVariable("CM64_TEXTURE_ATLAS") == "1";
        cameraProbe = Environment.GetEnvironmentVariable("CM64_CAMERA_PROBE") == "1";
        live = Environment.GetEnvironmentVariable("CM64_LIVE_CONTROLS") == "1";
        if (Environment.GetEnvironmentVariable("CM64_GOAL19_NATIVE_AUTOWARP") == "1" && (!live || !inOutput))
            throw new InvalidOperationException("Native auto-warp requires opt-in live image session");
        if (live)
        {
            if (!inOutput) throw new InvalidOperationException("Live input requires original OutputPanel hook");
            LiveMarioControls.VerifyHost();
            string trace = Environment.GetEnvironmentVariable("CM64_LIVE_TRACE") ?? "";
            string root = Path.GetFullPath(Path.Combine(Environment.GetFolderPath(
                Environment.SpecialFolder.LocalApplicationData), "CrashMarioFusion", "M43-input")) + Path.DirectorySeparatorChar;
            if (!Path.GetFullPath(trace).StartsWith(root, StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("Live telemetry must remain private in M43-input");
            liveTrace = new StreamWriter(new FileStream(trace, FileMode.CreateNew, FileAccess.Write, FileShare.Read)) { AutoFlush = true };
            LiveMarioControls.Start();
        }
        if (cameraProbe) CrashCameraProbe.Start();
        if (inOutput)
            OriginalMarioOutputOverlay.Register();
        else
            OriginalMarioPreview.Register(); // original diagnostic path preserved
        Event.AddListener<VSyncEvent>(OnHostVSync);
        // Explicit native Windows QA only: reuse the original host developer-menu warp
        // instead of guessing GUI keys or writing guest memory from this mod.
        // This is a menu transition, NOT evidence of Mario/Crash shared physics.
        if (Environment.GetEnvironmentVariable("CM64_GOAL19_NATIVE_AUTOWARP") == "1")
        {
            RecompOne.Runtime.Host.Cheats.CheatManager.RequestWarp(9, 1);
            Console.WriteLine("[cm64-goal19] HOST_DEV_WARP_REQUESTED level=9 map_slot=1 native_scene_unverified=true");
        }
        Console.WriteLine("[cm64-embedded] ARMED guest geometry mode=" +
            (inOutput ? "OUTPUT_IMAGE_OVERLAY" : "DIAGNOSTIC_PREVIEW") +
            "; native Crash collider/depth unchanged");
    }

    public void OnUnload()
    {
        lock (nativeLock) UnloadOwned();
    }

    void UnloadOwned()
    {
        if (live) LiveMarioControls.Stop();
        liveTrace?.Dispose(); liveTrace = null;
        if (enabled) Event.RemoveListener<VSyncEvent>(OnHostVSync);
        if (cameraProbe) CrashCameraProbe.Stop();
        enabled = false; halted = true;
        OriginalMarioOutputOverlay.Stop();
        if (textured) RecompOne.Runtime.Host.Window.OriginalMarioAtlas.ReleaseAtlas();
        OriginalMarioPreview.Stop();
        if (started && nativeThread != Environment.CurrentManagedThreadId)
        {
            Console.Error.WriteLine("[cm64-live] cleanup deferred to process exit: wrong native owner");
            return;
        }
        if (marioId >= 0) { MarioNative.sm64_mario_delete(marioId); marioId = -1; }
        if (started) { MarioNative.sm64_global_terminate(); started = false; }
        NativeMemory.Free(texture); texture = null;
        NativeMemory.Free(meshPositions); meshPositions = null;
        NativeMemory.Free(meshNormals); meshNormals = null;
        NativeMemory.Free(meshColors); meshColors = null;
        NativeMemory.Free(meshUv); meshUv = null;
    }

    void Initialize()
    {
        nativeThread = Environment.CurrentManagedThreadId;
        var info = new FileInfo(ownedMarioPath);
        if (info.Length != MarioNative.RomBytes)
            throw new InvalidOperationException("Mario ROM size rejected");
        var owned = File.ReadAllBytes(ownedMarioPath);
        try
        {
            if (Convert.ToHexString(SHA1.HashData(owned)) != OwnedMarioHash)
                throw new InvalidOperationException("Mario owned original SHA1 mismatch");
            texture = (byte*)NativeMemory.AllocZeroed(MarioNative.TextureBytes);
            meshPositions = (float*)NativeMemory.AllocZeroed(9216, 4);
            meshNormals = (float*)NativeMemory.AllocZeroed(9216, 4);
            meshColors = (float*)NativeMemory.AllocZeroed(9216, 4);
            meshUv = (float*)NativeMemory.AllocZeroed(6144, 4);
            if (texture == null || meshPositions == null || meshNormals == null ||
                meshColors == null || meshUv == null)
                throw new OutOfMemoryException();
            fixed (byte* rom = owned) MarioNative.sm64_global_init(rom, texture);
            started = true;
            if (textured)
            {
                byte[] rgba=new byte[MarioNative.TextureBytes];
                Marshal.Copy((nint)texture,rgba,0,rgba.Length);
                try { RecompOne.Runtime.Host.Window.OriginalMarioAtlas.QueueAtlas(rgba); }
                finally { CryptographicOperations.ZeroMemory(rgba); }
            }
        }
        finally { CryptographicOperations.ZeroMemory(owned); }

        MarioSurface* floor = stackalloc MarioSurface[2];
        MarioNative.AddAuthoredFloor(floor);
        MarioNative.sm64_static_surfaces_load(floor, 2);
        marioId = MarioNative.sm64_mario_create(0, 250, 0);
        if (marioId < 0) throw new InvalidOperationException("Native Mario actor create rejected");

        input = new MarioInputs { CamLookX = 1, CamLookZ = 0 };
        geometry = new MarioGeometry { Position=meshPositions, Normal=meshNormals,
            Color=meshColors, Uv=meshUv };
        lastTickTime = Stopwatch.GetTimestamp();
        Console.WriteLine("[cm64-embedded] INIT_OK in Crash process, authored platform only");
    }

    void OnHostVSync(VSyncEvent host)
    {
        lock (nativeLock) TickOwned(host);
    }

    void TickOwned(VSyncEvent host)
    {
        if (!enabled || halted) return;
        try
        {
            if (!started)
            {
                if (Stopwatch.GetTimestamp() - loadedAt < Stopwatch.Frequency / 2) return;
                Initialize();
            }
            long now = Stopwatch.GetTimestamp();
            if (nativeThread != Environment.CurrentManagedThreadId)
                throw new InvalidOperationException("Native Mario owner changed");
            MarioInputSnapshot snapshot = null;
            if (live)
            {
                if (ticks >= LiveMarioInput.MaxTicks) { halted = true; return; }
                if (!LiveMarioControls.SceneValid(now)) return;
                if (!LiveMarioControls.Input.TryTick(now, Stopwatch.Frequency, out input, out snapshot)) return;
                if (liveEpoch != snapshot.Epoch)
                {
                    MarioNative.sm64_mario_delete(marioId);
                    marioId = MarioNative.sm64_mario_create(0, 250, 0);
                    if (marioId < 0) throw new InvalidOperationException("Mario reset rejected");
                    liveEpoch = snapshot.Epoch;
                    ++liveActorEpoch;
                }
            }
            else
            {
                if (now - lastTickTime < Stopwatch.Frequency / 30) return;
                lastTickTime = now;
                if (ticks >= 180) { halted = true; return; }
            // Dedicated bounded original Mario simulation. No Crash input mutation.
            input.StickY = ticks >= 70 && ticks < 155 ? .75f : 0f;
            input.ButtonA = (byte)(ticks == 125 ? 1 : 0);
            }
            geometry.NumTrianglesUsed = 0;
            fixed (MarioInputs* inputs = &input)
            fixed (MarioState* output = &state)
            fixed (MarioGeometry* buffers = &geometry)
                MarioNative.sm64_mario_tick(marioId, inputs, output, buffers);
            if (!float.IsFinite(state.Position[0]) || !float.IsFinite(state.Position[1]) ||
                !float.IsFinite(state.Position[2]) ||
                geometry.NumTrianglesUsed > MarioNative.MaxTriangles)
                throw new InvalidOperationException("Non-finite Mario state/invalid mesh count");
            if (geometry.NumTrianglesUsed > 0) geometryFrames++;
            OriginalMarioPreview.Publish(geometry.Position, geometry.Color, geometry.Uv, geometry.NumTrianglesUsed, ticks+1);
            if (Math.Abs(state.Velocity[0]) + Math.Abs(state.Velocity[2]) > .005f)
                movingFrames++;
            ++ticks;
            if (live)
            {
                liveTrace.WriteLine(JsonSerializer.Serialize(new { schema = 1, tick = ticks,
                    hostFrame = host.Frame, timestamp = now, frequency = Stopwatch.Frequency,
                    sequence = snapshot.Sequence, epoch = snapshot.Epoch, actorEpoch = liveActorEpoch,
                    stickX = input.StickX, stickY = input.StickY, jump = input.ButtonA != 0,
                    x = state.Position[0], y = state.Position[1], z = state.Position[2],
                    vx = state.Velocity[0], vy = state.Velocity[1], vz = state.Velocity[2],
                    action = state.Action, surface = "AUTHORED_NOT_CRASH" }));
                if (state.Position[1] < -500 || Math.Abs(state.Position[0]) > 1500 ||
                    Math.Abs(state.Position[2]) > 1500)
                    liveEpoch = -1;
            }
            if (!live && ticks == 180)
            {
                Console.WriteLine("[cm64-embedded] HOST_SOLVER frames=180 mesh_frames=" +
                    geometryFrames + " moving_frames=" + movingFrames +
                    " surface=AUTHORED_NOT_CRASH drawing=" +
                    (inOutput ? "OUTPUT_IMAGE_OVERLAY" : "DIAGNOSTIC_PREVIEW_ONLY") +
                    " physical_status=BLOCKED");
                halted = true;
            }
        }
        catch (Exception e)
        {
            Console.Error.WriteLine("[cm64-embedded] FAIL_CLOSED " + e.GetType().Name);
            halted = true;
            if (live) UnloadOwned();
            // Cleanup on mod unloading; never throw into Crash's game event bus.
        }
    }
}
