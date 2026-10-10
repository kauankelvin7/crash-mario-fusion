using System.Buffers.Binary;
using RecompOne.Runtime;
using RecompOne.Runtime.Context;
using RecompOne.Runtime.Memory;

namespace RecompOne.Runtime.Memory
{
    public interface IMemory { void WriteU32(uint address, uint value); }
    public sealed class PSMemory : IMemory
    {
        public byte[] Bytes = new byte[0x200000], ScratchBytes = new byte[1024];
        public ReadOnlySpan<byte> Ram => Bytes;
        internal ReadOnlySpan<byte> CM64Scratchpad => ScratchBytes;
        public void WriteU32(uint address, uint value) =>
            BinaryPrimitives.WriteUInt32LittleEndian(Bytes.AsSpan((int)(address & 0x1FFFFFFF), 4), value);
    }
}
namespace RecompOne.Runtime.Catalogs
{
    public enum LevelKind { Gameplay }
    public sealed class Info { public LevelKind Kind => LevelKind.Gameplay; }
    public sealed class Levels
    {
        public bool TryGet(uint level, out Info info) { info = new Info(); return level == 9; }
    }
    public static class Catalog
    {
        public const uint LevelIdAddr = 0x80056710;
        public static readonly Levels Levels = new();
    }
}
namespace RecompOne.Runtime.Hle { public static class GpuHle { public static bool Active => false; } }
namespace RecompOne.Runtime
{
    public static class GteScreenCache
    {
        public static bool AddressTagged => false;
        public static void Store(int sx, int sy, float fx, float fy, float z) { }
        public static void StoreAt(uint address, uint word, float fx, float fy, float z) { }
    }
}

public static class Fixture
{
    static void ReadOnly(PSMemory memory, Action action)
    {
        byte[] ram = (byte[])memory.Bytes.Clone(), scratch = (byte[])memory.ScratchBytes.Clone();
        uint[] registers = Enumerable.Range(0, 32).Select(Gte.Read).ToArray();
        uint[] controls = Enumerable.Range(0, 32).Select(Gte.ReadControl).ToArray();
        action();
        if (!memory.Bytes.SequenceEqual(ram) || !memory.ScratchBytes.SequenceEqual(scratch) ||
            !registers.SequenceEqual(Enumerable.Range(0, 32).Select(Gte.Read)) ||
            !controls.SequenceEqual(Enumerable.Range(0, 32).Select(Gte.ReadControl)))
            throw new InvalidOperationException("Probe altered native memory/GTE state");
    }

    public static void Main(string[] args)
    {
        string scenario = args.Length == 0 ? "valid" : args[0];
        var memory = new PSMemory();
        uint zone = 0x80001000, zoneHeader = 0x80001100, header = 0x80002000;
        uint polygons = 0x80003000, vertices = 0x80004000, primitive = 0x80005000;
        uint ids = 0x80006000, ot = 0x80010000;
        memory.WriteU32(RecompOne.Runtime.Catalogs.Catalog.LevelIdAddr, 9);
        memory.WriteU32(0x80057914, zone); memory.WriteU32(0x8005791C, 0x80007000);
        memory.WriteU32(0x80057960, 7);
        memory.WriteU32(zone, 0x0100FFFF); memory.WriteU32(zone + 16, zoneHeader);
        memory.WriteU32(zoneHeader, 1);
        uint[] descriptor = [0x12345678, 0, 0, 0, header, polygons, vertices, 0x80008000];
        for (int index = 0; index < descriptor.Length; index++)
        {
            memory.WriteU32(zoneHeader + 4 + (uint)index * 4, descriptor[index]);
            BinaryPrimitives.WriteUInt32LittleEndian(memory.ScratchBytes.AsSpan(0x100 + index * 4, 4), descriptor[index]);
        }
        memory.WriteU32(header + 12, 1); memory.WriteU32(header + 16, 3);
        memory.WriteU32(polygons, 2u << 20); memory.WriteU32(polygons + 4, 1u << 8);
        int[][] xyz = [[-128, -128, 1024], [128, -128, 1024], [0, 128, 1024]];
        for (int index = 0; index < 3; index++)
        {
            int x = xyz[index][0], y = xyz[index][1], z = xyz[index][2];
            uint low = (uint)((z >> 3) & 255) << 24;
            uint high = ((uint)(ushort)x & 0xFFF8) | (((uint)(ushort)y & 0xFFF8) << 16);
            memory.WriteU32(vertices + (uint)index * 8, low);
            memory.WriteU32(vertices + (uint)index * 8 + 4, high);
            Gte.Write(index * 2, ((uint)(ushort)y << 16) | (ushort)x);
            Gte.Write(index * 2 + 1, (uint)z);
        }
        int[] rotation = scenario == "rotated" ? [3547, 0, 2048, 0, 4096, 0, -2048, 0, 3547] : [4096, 0, 0, 0, 4096, 0, 0, 0, 4096];
        for (int index = 0; index < 5; index++)
        {
            uint packed = (ushort)rotation[index * 2];
            if (index * 2 + 1 < 9) packed |= (uint)(ushort)rotation[index * 2 + 1] << 16;
            Gte.WriteControl(index, packed); memory.WriteU32(0x800577E4 + (uint)index * 4, packed);
        }
        Gte.WriteControl(24, 160 << 16); Gte.WriteControl(25, 120 << 16); Gte.WriteControl(26, 256);
        if (scenario == "saturated") Gte.WriteControl(26, 2048);
        if (scenario == "rotated")
        {
            memory.WriteU32(0x80057864, 8192); memory.WriteU32(header, 64); memory.WriteU32(header + 8, 64);
            int[] relative = [32, 0, 64];
            for (int axis = 0; axis < 3; axis++)
            {
                int transformed = Enumerable.Range(0, 3).Sum(column => rotation[axis * 3 + column] * relative[column]) >> 12;
                Gte.WriteControl(5 + axis, unchecked((uint)transformed));
                memory.WriteU32(zoneHeader + 8 + (uint)axis * 4, unchecked((uint)transformed));
                BinaryPrimitives.WriteUInt32LittleEndian(memory.ScratchBytes.AsSpan(0x104 + axis * 4, 4), unchecked((uint)transformed));
            }
            Gte.WriteControl(26, 317); Gte.WriteControl(24, (160 << 16) + 123); Gte.WriteControl(25, (120 << 16) + 456);
        }
        var cpu = new CpuContext { A0 = ot, T2 = ids + 2, T3 = primitive, T4 = 0, S7 = polygons, T8 = vertices };
        if (scenario != "no-ot") CrashWorldSourceProbe.OrderingTable(ot + 8188, 2048);
        if (scenario == "bad-ot") cpu.A0 += 4;
        if (scenario == "paused") memory.WriteU32(0x80056400, 1);
        if (scenario == "wrong-call") cpu.A0 = ot;
        ReadOnly(memory, () => CrashWorldSourceProbe.Enter(scenario == "wrong-call" ? 0x80019BCCu : 0x80019508u, cpu, memory));
        if (scenario == "bad-scratch") memory.ScratchBytes[0x100] ^= 1;
        if (scenario == "bad-vertex") memory.Bytes[(int)(vertices & 0x1FFFFFFF) + 4] ^= 8;
        if (scenario == "bad-matrix") memory.WriteU32(0x800577E4, 4095);
        ReadOnly(memory, () => CrashWorldSourceProbe.BeforeGte(0x4A280030));
        Gte.Execute(0x4A280030);
        ReadOnly(memory, () => CrashWorldSourceProbe.AfterGte(0x4A280030));
        int[] packetOffsets = scenario == "gt3" ? [8, 20, 32] : [8, 16, 24];
        for (int index = 0; index < 3; index++) memory.WriteU32(primitive + (uint)packetOffsets[index], Gte.Read(12 + index));
        memory.WriteU32(primitive + 4, scenario == "gt3" ? 0x36000000u : 0x30000000u);
        memory.WriteU32(primitive, scenario == "gt3" ? 0x09FFFFFFu : 0x06FFFFFFu);
        memory.WriteU32(ot, primitive & 0xFFFFFF);
        if (scenario == "frame-drift") memory.WriteU32(0x80057960, 8);
        if (scenario == "zone-drift") memory.WriteU32(0x80057914, zone + 4);
        if (scenario == "zone-header-drift") memory.WriteU32(zone + 16, zoneHeader + 4);
        if (scenario == "zone-magic-drift") memory.WriteU32(zone, 0);
        if (scenario == "world-count-drift") memory.WriteU32(zoneHeader, 0);
        if (scenario == "poly-id-drift") memory.WriteU32(ids + 4, 1);
        if (scenario == "camera-drift") memory.WriteU32(0x80057864, 256);
        if (scenario == "missing-link") memory.WriteU32(ot, 0xFFFFFF);
        if (scenario == "bad-sxy") memory.WriteU32(primitive + 8, 0);
        if (scenario == "ot-reset") CrashWorldSourceProbe.OrderingTable(ot + 8188, 2048);
        ReadOnly(memory, () => CrashWorldSourceProbe.Leave(0x80019508, scenario != "guest-throw"));
        Console.WriteLine("VERIFIED_SYNTHETIC fixture=" + scenario + " memory_gte_unchanged=true original_game_NOT_TESTED");
    }
}
