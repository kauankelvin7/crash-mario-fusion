using System;
using System.Buffers.Binary;
using System.Net;
using System.Net.Sockets;
using RecompOne.Runtime.Catalogs;
using RecompOne.Runtime.Events;
using RecompOne.Runtime.Hardware;
using RecompOne.Runtime.Memory;
using RecompOne.Runtime.Modding;

// SCUS-94900 / Launcher 224da775 only. PadRead is NOT a physics boundary.
// No IMemory reads: PSMemory.ReadU32 can call CountAccess/MaybeCatchUpVBlank.
public sealed class CrashPoseMod : IMod
{
    private Socket socket;
    private readonly byte[] packet = new byte[80];
    private long started, nextSend, lastCallback;
    private uint sequence, tick, epoch, level, obj, kind, global, external;
    private PSMemory memory;
    private bool valid;
    private int attempts;
    private static bool Fits(uint address, int size) =>
        (address & 3) == 0 && address >= 0x80000000u && address <= 0x80200000u - size;
    private static uint Read(ReadOnlySpan<byte> ram, uint address) =>
        BinaryPrimitives.ReadUInt32LittleEndian(ram.Slice(checked((int)(address - 0x80000000u)), 4));
    private void Put(int offset, uint value) => BinaryPrimitives.WriteUInt32BigEndian(packet.AsSpan(offset), value);

    public void OnLoad()
    {
        if (Environment.GetEnvironmentVariable("CM64_CRASH_POSE_ENABLE") != "1") return;
        string token = Environment.GetEnvironmentVariable("CM64_CRASH_POSE_SESSION");
        if (token == null || token.Length != 32 ||
            !int.TryParse(Environment.GetEnvironmentVariable("CM64_CRASH_POSE_PORT"), out int port) || port < 1024 || port > 65535)
            throw new InvalidOperationException("Invalid Crash observer session/port");
        byte[] session = Convert.FromHexString(token);
        if (Array.TrueForAll(session, b => b == 0)) throw new InvalidOperationException("Zero session");
        socket = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp);
        try { socket.Blocking = false; socket.Connect(new IPEndPoint(IPAddress.Loopback, port)); }
        catch { socket.Dispose(); socket = null; throw; }
        packet[0] = (byte)'C'; packet[1] = (byte)'M'; packet[2] = (byte)'W'; packet[3] = (byte)'1';
        packet[4] = 1; // Crash; phase=0 UNKNOWN_DIAGNOSTIC, flags=0.
        session.CopyTo(packet, 8);
        packet[24] = (byte)'M'; packet[25] = (byte)'3'; packet[26] = (byte)'2'; packet[27] = (byte)'D';
        sequence = tick = epoch = 0; attempts = 0; valid = false; memory = null;
        started = Environment.TickCount64; nextSend = started; lastCallback = started;
        Event.AddListener<PadReadEvent>(OnPad);
        Console.WriteLine("[cm64-crash-pose] ready phase=UNKNOWN tick=observer_pad_callback NOT_CALIBRATION_READY");
    }
    public void OnUnload()
    {
        Event.RemoveListener<PadReadEvent>(OnPad);
        socket?.Dispose(); socket = null; memory = null; valid = false;
    }
    private void OnPad(PadReadEvent e)
    {
        if (socket == null || e.Port != 0) return;
        long now = Environment.TickCount64;
        if (now - started >= 300000 || attempts >= 3000 || tick == uint.MaxValue || epoch == uint.MaxValue)
        { OnUnload(); return; }
        ++tick; // Observer ordinal, NOT a native simulation tick.
        if (now - lastCallback > 250) valid = false;
        lastCallback = now;
        try
        {
            if (e.Memory is not PSMemory m || m.Ram.Length != 0x200000)
            { valid = false; return; }
            ReadOnlySpan<byte> ram = m.Ram;
            uint levelAddress = Catalog.LevelIdAddr;
            if (!Fits(levelAddress, 4)) { valid = false; return; }
            uint currentLevel = Read(ram, levelAddress);
            // Conservative: either native pause flag or Start request suppresses sampling.
            // A stale pause flag can suppress a valid sample, never certify unpaused physics.
            if (!Catalog.Levels.TryGet(currentLevel, out var info) || info.Kind != LevelKind.Gameplay ||
                Read(ram, 0x80056400u) != 0 || Read(ram, 0x8005640Cu) != 0 ||
                (e.Buttons & Controller.Start) == 0)
            { valid = false; return; }
            uint currentObj = Read(ram, 0x800566B4u);
            if (!Fits(currentObj, 0x124)) { valid = false; return; }
            uint currentKind = Read(ram, currentObj);
            // Same active-object discriminator as pinned SnapshotObject; not an allocation generation.
            if (currentKind is 0 or 2) { valid = false; return; }
            uint currentGlobal = Read(ram, currentObj + 0x20), currentExternal = Read(ram, currentObj + 0x24);
            if (!valid || memory != m || level != currentLevel || obj != currentObj || kind != currentKind ||
                global != currentGlobal || external != currentExternal)
            {
                ++epoch;
                memory = m; level = currentLevel; obj = currentObj; kind = currentKind;
                global = currentGlobal; external = currentExternal; valid = true;
            }
            if (now < nextSend) return;
            nextSend = now + 100; // <=10 Hz; no catch-up sends after stalls.
            Put(28, level); Put(32, epoch); Put(36, 0); // M32D + source level + observer epoch + reserved.
            Put(40, ++sequence); Put(44, tick);
            // Native signed xyz and rotation: preserve two's-complement bits without conversion.
            for (uint i = 0; i < 6; ++i) Put(48 + (int)i * 4, Read(ram, obj + 0x80 + i * 4));
            Put(72, Read(ram, obj + 0x2C)); Put(76, Read(ram, obj + 0x120));
            ++attempts;
            try { socket.Send(packet); }
            catch (SocketException) { /* Drop, never retry or block gameplay. */ }
        }
        catch (Exception)
        {
            // Unexpected layout/API failures disable the observer, never escape into the game bus.
            OnUnload();
        }
    }
}
