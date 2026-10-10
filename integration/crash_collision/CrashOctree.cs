using System;
using System.Buffers.Binary;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;

public sealed record CrashVolume(int Node, int Depth, int[] Min, int[] Max);
public sealed record CrashZone(uint Entry, uint Eid, uint EntryType, uint RectAddress,
    uint RectEnd, string Digest, int[] Min, int[] Max, int[] Depths, CrashVolume[] Volumes);

public static class CrashOctree
{
    public const uint Base = 0x80000000;
    public const int RamSize = 0x200000;
    public const int MaxLeaves = 4096;
    public static bool Fits(uint address, int size) => size >= 0 && size <= RamSize &&
        address >= Base && address <= Base + RamSize - (uint)size;
    public static uint U32(ReadOnlySpan<byte> ram, uint address)
    {
        if (ram.Length != RamSize || (address & 3) != 0 || !Fits(address, 4))
            throw new InvalidDataException("RAM_ADDRESS");
        return BinaryPrimitives.ReadUInt32LittleEndian(ram.Slice((int)(address - Base), 4));
    }
    public static CrashZone Read(ReadOnlySpan<byte> ram, uint entry)
    {
        if (U32(ram, entry) != 0x100FFFF) throw new InvalidDataException("ENTRY_MAGIC");
        uint count = U32(ram, checked(entry + 12));
        if (count < 2 || count > 128 || !Fits(entry, checked(16 + ((int)count + 1) * 4)))
            throw new InvalidDataException("ITEM_COUNT");
        uint previous = checked(entry + 16 + (count + 1) * 4);
        for (uint index = 0; index <= count; ++index)
        {
            uint item = U32(ram, checked(entry + 16 + index * 4));
            if ((item & 1) != 0 || !Fits(item, 0) || item < previous)
                throw new InvalidDataException("ITEM_SPAN");
            previous = item;
        }
        uint start = U32(ram, checked(entry + 20)), end = U32(ram, checked(entry + 24));
        if (end - start < 36 || end - start > 65536) throw new InvalidDataException("RECT_SPAN");
        byte[] data = ram.Slice((int)(start - Base), (int)(end - start)).ToArray();
        int[] low = new int[3], high = new int[3], dimensions = new int[3], depths = new int[3];
        for (int axis = 0; axis < 3; ++axis)
        {
            long origin = BinaryPrimitives.ReadInt32LittleEndian(data.AsSpan(axis * 4, 4));
            long size = BinaryPrimitives.ReadUInt32LittleEndian(data.AsSpan(12 + axis * 4, 4));
            if (size <= 0 || size > int.MaxValue / 256 || origin * 256 < int.MinValue ||
                (origin + size) * 256 > int.MaxValue)
                throw new InvalidDataException("RECT_BOUNDS");
            low[axis] = checked((int)(origin * 256));
            dimensions[axis] = checked((int)(size * 256));
            high[axis] = checked(low[axis] + dimensions[axis]);
            depths[axis] = BinaryPrimitives.ReadUInt16LittleEndian(data.AsSpan(30 + axis * 2, 2));
            if (depths[axis] > 16) throw new InvalidDataException("DEPTH_LIMIT");
        }
        var volumes = new List<CrashVolume>();
        var ancestors = new HashSet<int>();
        int visits = 0;
        Walk(data, BinaryPrimitives.ReadUInt16LittleEndian(data.AsSpan(28, 2)), 0,
            low, dimensions, depths, ancestors, volumes, ref visits);
        if (volumes.Count == 0) throw new InvalidDataException("EMPTY_OCTREE");
        return new CrashZone(entry, U32(ram, entry + 4), U32(ram, entry + 8), start, end,
            Convert.ToHexString(SHA256.HashData(data)).ToLowerInvariant(), low, high, depths,
            volumes.ToArray());
    }
    private static void Walk(byte[] data, int node, int depth, int[] low, int[] size,
        int[] depths, HashSet<int> ancestors, List<CrashVolume> volumes, ref int visits)
    {
        if (++visits > 8192 || depth > 16) throw new InvalidDataException("TRAVERSAL_LIMIT");
        if (node == 0) return;
        if ((node & 1) != 0)
        {
            if (volumes.Count >= MaxLeaves) throw new InvalidDataException("LEAF_LIMIT");
            int[] high = new int[3];
            for (int axis = 0; axis < 3; ++axis) high[axis] = checked(low[axis] + size[axis]);
            volumes.Add(new CrashVolume(node, depth, (int[])low.Clone(), high));
            return;
        }
        int[] splits = new int[3], childSize = new int[3];
        int children = 1;
        for (int axis = 0; axis < 3; ++axis)
        {
            splits[axis] = depth < depths[axis] ? 1 : 0;
            children *= 1 + splits[axis];
            childSize[axis] = size[axis] >> splits[axis];
            if (childSize[axis] == 0 || (splits[axis] == 1 && (size[axis] & 1) != 0))
                throw new InvalidDataException("NONEXACT_SUBDIVISION");
        }
        if (children == 1 || node < 36 || node > data.Length - children * 2 || !ancestors.Add(node))
            throw new InvalidDataException("CHILD_SPAN_OR_CYCLE");
        int index = 0;
        for (int x = 0; x <= splits[0]; ++x)
            for (int y = 0; y <= splits[1]; ++y)
                for (int z = 0; z <= splits[2]; ++z)
                {
                    int[] childLow = { checked(low[0] + x * childSize[0]),
                        checked(low[1] + y * childSize[1]), checked(low[2] + z * childSize[2]) };
                    int child = BinaryPrimitives.ReadUInt16LittleEndian(data.AsSpan(node + index++ * 2, 2));
                    Walk(data, child, depth + 1, childLow, childSize, depths, ancestors, volumes, ref visits);
                }
        ancestors.Remove(node);
    }
}
