using System;
using System.Buffers.Binary;
using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using RecompOne.Runtime.Catalogs;
using RecompOne.Runtime.Events;
using RecompOne.Runtime.Hardware;
using RecompOne.Runtime.Modding;

// Native PadReadEvent integration, not a replacement for Crash's movement.
public sealed class CoinJumpMod : IMod
{
    private Socket socket;
    private byte[] session;
    private uint lastSequence;
    private long pulseUntil, releaseUntil;
    private uint? level;
    private bool apply;
    private bool keyboardArm, previousR1, armConsumed;
    private long armedUntil;
    // NTSC-U SCUS-94900: addresses/offsets corroborated in pinned FramePacing.cs.
    // Diagnostic only: never writes Crash RAM, changes speed, or alters physics.
    private const uint CrashPointer = 0x800566B4u;
    private const uint TranslationY = 0x84u, VelocityY = 0xA8u;
    private const uint State = 0x2Cu, StateFlags = 0x120u, StatusA = 0xC8u;
    private long motionUntil, nextMotionSample;
    private uint motionSequence, motionObject;
    private int motionSamples, motionStartY, motionMinY, motionMaxY, motionEndY;
    private bool motionAirSeen, motionGroundAfterAir;
    public int AppliedCount { get; private set; }
    public int ObservedCount { get; private set; }
    public void OnLoad()
    {
        string token = Environment.GetEnvironmentVariable("CM64_SESSION");
        if (token == null && Environment.GetEnvironmentVariable("CM64_PORT") == null)
        { Console.WriteLine("[cm64] disabled; use the paired integration runner"); return; }
        if (token == null || token.Length != 32) throw new InvalidOperationException("CM64_SESSION must be 32 hex digits");
        session = Convert.FromHexString(token);
        if (!int.TryParse(Environment.GetEnvironmentVariable("CM64_PORT"), out int port) || port < 1024 || port > 65535)
            throw new InvalidOperationException("Invalid CM64_PORT");
        apply = Environment.GetEnvironmentVariable("CM64_APPLY") == "1";
        keyboardArm = apply && Environment.GetEnvironmentVariable("CM64_KEYBOARD_ARM") == "1";
        socket = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp);
        try { socket.Bind(new IPEndPoint(IPAddress.Loopback, port)); socket.Blocking = false; }
        catch { socket.Dispose(); socket = null; throw; }
        Event.AddListener<PadReadEvent>(OnPad);
        Console.WriteLine($"[cm64] receiver ready port={port} apply={apply} keyboard_arm={keyboardArm}; " +
            (keyboardArm ? "tap W (R1) in Crash gameplay to arm ONE jump for 60s" :
                           "HOLD R1 only during unpaused gameplay to permit a pulse"));
    }
    public void OnUnload()
    {
        Event.RemoveListener<PadReadEvent>(OnPad);
        if (motionUntil != 0) FinishMotion("unloaded");
        socket?.Dispose(); socket = null; pulseUntil = releaseUntil = armedUntil = 0;
        armConsumed = previousR1 = false;
    }
    private void OnPad(PadReadEvent e)
    {
        var receiver = socket;
        if (e.Port != 0 || receiver == null) return;
        long now = Environment.TickCount64;
        uint currentLevel = e.Memory.ReadU32(Catalog.LevelIdAddr);
        bool gameplay = Catalog.Levels.TryGet(currentLevel, out var info) && info.Kind == LevelKind.Gameplay;
        bool safeContext = apply && gameplay && (e.Buttons & Controller.Start) != 0;
        if (motionUntil != 0 && (level != currentLevel || !safeContext))
            FinishMotion("level_changed_or_paused");
        bool r1Down = (e.Buttons & Controller.R1) == 0;
        if (level != currentLevel || !safeContext)
        {
            pulseUntil = releaseUntil = armedUntil = 0;
            armConsumed = true;
        }
        level = currentLevel;
        if (keyboardArm && safeContext && r1Down && !previousR1)
        {
            armedUntil = now + 60000;
            armConsumed = false;
            Console.WriteLine($"[cm64] keyboard armed crash_level={currentLevel} expires_in_ms=60000");
        }
        previousR1 = r1Down;
        bool permitted = safeContext && (keyboardArm ? now < armedUntil : r1Down);
        bool mayApplyEvent = permitted && (!keyboardArm || !armConsumed);
        if (!permitted) pulseUntil = releaseUntil = 0;
        byte[] packet = new byte[256];
        // Bounded drain; no background thread, backlog or blocking game-loop work.
        for (int n = 0; n < 32; n++)
        {
            int length;
            try { length = receiver.Receive(packet); }
            catch (SocketException ex) when (ex.SocketErrorCode == SocketError.WouldBlock) { break; }
            catch (SocketException ex) when (ex.SocketErrorCode == SocketError.MessageSize) { continue; }
            catch (ObjectDisposedException) { return; }
            if (length != 52 || packet[0] != 'C' || packet[1] != 'M' || packet[2] != 'J' || packet[3] != '1') continue;
            bool matches = true;
            for (int i = 0; i < 16; i++) matches &= packet[4+i] == session[i];
            if (!matches) continue;
            uint sequence = BinaryPrimitives.ReadUInt32BigEndian(packet.AsSpan(20));
            long stamp = BinaryPrimitives.ReadInt64BigEndian(packet.AsSpan(44));
            long age = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() - stamp;
            if (sequence == 0 || sequence <= lastSequence) continue;
            lastSequence = sequence; // Expired/ineligible packets are consumed, never replayed.
            if (age < -100 || age > 250) { Console.WriteLine($"[cm64] drop seq={sequence} stale age_ms={age}"); continue; }
            int coins = BinaryPrimitives.ReadInt32BigEndian(packet.AsSpan(28));
            float x = ReadFloat(packet,32), y = ReadFloat(packet,36), z = ReadFloat(packet,40);
            if (coins < 0 || coins > short.MaxValue || !float.IsFinite(x) || !float.IsFinite(y) || !float.IsFinite(z)) continue;
            uint tick = BinaryPrimitives.ReadUInt32BigEndian(packet.AsSpan(24));
            ObservedCount++;
            Console.WriteLine(FormattableString.Invariant($"[cm64] received seq={sequence} mario_tick={tick} coins={coins} pos={x},{y},{z} crash_level={currentLevel}"));
            if (!mayApplyEvent || now < releaseUntil || (e.Buttons & Controller.Cross) == 0)
            { Console.WriteLine($"[cm64] observe-only/drop seq={sequence}"); continue; }
            pulseUntil = now + 100; releaseUntil = now + 200;
            if (keyboardArm) { armConsumed = true; mayApplyEvent = false; }
            AppliedCount++;
            if (motionUntil != 0) FinishMotion("superseded");
            motionSequence = sequence;
            motionUntil = now + 3500; nextMotionSample = now;
            motionObject = 0; motionSamples = 0;
            motionAirSeen = motionGroundAfterAir = false;
            Console.WriteLine($"[cm64] input_applied seq={sequence}; collecting native motion for 3500ms; jump/landing NOT_VERIFIED");
        }
        if (permitted && now < pulseUntil) e.Buttons = (ushort)(e.Buttons & ~Controller.Cross);
        // At expiry original physical input is restored; never force-release a user's button.
        if (motionUntil != 0)
        {
            if (!gameplay || level != currentLevel) FinishMotion("level_or_menu");
            else SampleMotion(e, now);
        }
    }
    private void SampleMotion(PadReadEvent e, long now)
    {
        if (now >= motionUntil) { FinishMotion("window_complete"); return; }
        if (now < nextMotionSample) return;
        nextMotionSample = now + 120;
        try
        {
            uint obj = e.Memory.ReadU32(CrashPointer);
            // Reject pointers outside retail PS1 RAM, or objects too close to its end.
            if (obj < 0x80000000u || obj > 0x801FFE00u)
            { FinishMotion("invalid_player_pointer"); return; }
            if (motionSamples != 0 && obj != motionObject)
            { FinishMotion("player_replaced"); return; }
            int y = unchecked((int)e.Memory.ReadU32(obj + TranslationY));
            int vy = unchecked((int)e.Memory.ReadU32(obj + VelocityY));
            uint state = e.Memory.ReadU32(obj + State);
            uint flags = e.Memory.ReadU32(obj + StateFlags);
            uint status = e.Memory.ReadU32(obj + StatusA);
            if (motionSamples == 0)
            {
                motionObject = obj; motionStartY = motionMinY = motionMaxY = y;
            }
            motionSamples++; motionEndY = y;
            motionMinY = Math.Min(motionMinY, y); motionMaxY = Math.Max(motionMaxY, y);
            bool air = (flags & 0x8u) != 0;
            motionAirSeen |= air;
            if (motionAirSeen && !air && (status & 0x1u) != 0)
                motionGroundAfterAir = true;
            Console.WriteLine($"[cm64] motion_sample seq={motionSequence} n={motionSamples} y_raw={y} vy_raw={vy} state={state} air_flag={air} groundland_flag={((status & 1u) != 0)}");
        }
        catch (Exception ex)
        {
            FinishMotion("memory_error_" + ex.GetType().Name);
        }
    }
    private void FinishMotion(string reason)
    {
        if (motionUntil == 0) return;
        bool riseAndLandingCandidate = motionSamples >= 3 && motionMaxY > motionStartY && motionAirSeen && motionGroundAfterAir;
        Console.WriteLine($"[cm64] motion_summary seq={motionSequence} reason={reason} samples={motionSamples} y_start={motionStartY} y_min={motionMinY} y_max={motionMaxY} y_last={motionEndY} air_flag_seen={motionAirSeen} ground_after_air={motionGroundAfterAir} rise_and_landing_candidate={riseAndLandingCandidate} interpretation=OBSERVATION_ONLY");
        motionUntil = nextMotionSample = 0;
    }
    private static float ReadFloat(byte[] data, int offset) =>
        BitConverter.Int32BitsToSingle(BinaryPrimitives.ReadInt32BigEndian(data.AsSpan(offset)));
}
