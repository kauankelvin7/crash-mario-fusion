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
        socket = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp);
        try { socket.Bind(new IPEndPoint(IPAddress.Loopback, port)); socket.Blocking = false; }
        catch { socket.Dispose(); socket = null; throw; }
        Event.AddListener<PadReadEvent>(OnPad);
        Console.WriteLine($"[cm64] receiver ready port={port} apply={apply}; HOLD R1 only during unpaused gameplay to permit a pulse");
    }
    public void OnUnload()
    {
        Event.RemoveListener<PadReadEvent>(OnPad);
        socket?.Dispose(); socket = null; pulseUntil = releaseUntil = 0;
    }
    private void OnPad(PadReadEvent e)
    {
        var receiver = socket;
        if (e.Port != 0 || receiver == null) return;
        long now = Environment.TickCount64;
        uint currentLevel = e.Memory.ReadU32(Catalog.LevelIdAddr);
        bool gameplay = Catalog.Levels.TryGet(currentLevel, out var info) && info.Kind == LevelKind.Gameplay;
        bool permitted = apply && gameplay && (e.Buttons & Controller.R1) == 0
            && (e.Buttons & Controller.Start) != 0;
        if (level != currentLevel || !permitted) pulseUntil = releaseUntil = 0;
        level = currentLevel;
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
            if (!permitted || now < releaseUntil || (e.Buttons & Controller.Cross) == 0)
            { Console.WriteLine($"[cm64] observe-only/drop seq={sequence}"); continue; }
            pulseUntil = now + 100; releaseUntil = now + 200;
            AppliedCount++;
            Console.WriteLine($"[cm64] input_applied seq={sequence}; native jump/landing NOT_VERIFIED");
        }
        if (permitted && now < pulseUntil) e.Buttons = (ushort)(e.Buttons & ~Controller.Cross);
        // At expiry original physical input is restored; never force-release a user's button.
    }
    private static float ReadFloat(byte[] data, int offset) =>
        BitConverter.Int32BitsToSingle(BinaryPrimitives.ReadInt32BigEndian(data.AsSpan(offset)));
}
