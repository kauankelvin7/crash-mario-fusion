using System;
using System.Buffers.Binary;
using System.Collections.Generic;
using System.IO;

public sealed record CrashQueryNode(ushort Compact, int ReconstructedNode, int Depth,
    int[] Relative16, int[] Min, int[] Max);
public sealed record CrashQueryNeighbor(uint Slot, uint ReferenceBefore, uint ReferenceAfter,
    CrashZoneRect Source, bool Intersects, CrashQueryNode[] Nodes);
public sealed record CrashQueryReceipt(long ObservationEpoch, uint Query, uint Actor, uint Zone,
    uint Path, int[] Input, int[] BoundMin, int[] BoundMax, int ResultCount,
    CrashQueryNeighbor[] Neighbors)
{
    public bool AllocationGenerationKnown => false;
    public bool NativeFrameKnown => false;
    public bool MaterialMappingKnown => false;
    public bool SurfacesAllowed => false;
}

public sealed class CrashNativeQuery
{
    public const int QuerySize = 0x1050;
    public const int CountOffset = 0x1004;
    public const int BoundOffset = 0x1008;
    public const int NeighborCountOffset = 0x210;
    public const int NeighborOffset = 0x214;
    private readonly object owner;
    private readonly int thread;
    private readonly long epoch;
    private readonly uint query, actor, zone, path, header;
    private readonly CrashZoneRect zoneSource;
    private readonly uint[] references;
    private readonly int[] input = new int[3], low = new int[3], high = new int[3];
    private readonly List<CrashQueryNeighbor> neighbors = new();
    private bool consumed, lookupStarted;

    public CrashNativeQuery(ReadOnlySpan<byte> ram, object memoryOwner, int nativeThread,
        long observationEpoch, uint vector, uint objectArgument, uint queryAddress)
    {
        if (memoryOwner == null || nativeThread <= 0 || observationEpoch <= 0)
            throw new InvalidDataException("OWNER");
        owner = memoryOwner; thread = nativeThread; epoch = observationEpoch;
        actor = CrashOctree.U32(ram, 0x800566B4);
        zone = CrashOctree.U32(ram, 0x80057914);
        path = CrashOctree.U32(ram, 0x8005791C);
        query = queryAddress;
        CheckScene(ram);
        if (objectArgument != actor || !CrashOctree.Fits(vector, 12) ||
            !CrashOctree.Fits(query, QuerySize) || (query & 3) != 0)
            throw new InvalidDataException("QUERY_ARGUMENT");
        zoneSource = CrashOctree.ReadRect(ram, zone);
        if (zoneSource.EntryType != 7) throw new InvalidDataException("ZONE_TYPE");
        header = CrashOctree.U32(ram, zone + 16);
        if (!CrashOctree.Fits(header, NeighborOffset + 32) ||
            CrashOctree.U32(ram, zone + 20) < header + NeighborOffset + 32)
            throw new InvalidDataException("HEADER_SPAN");
        uint count = CrashOctree.U32(ram, header + NeighborCountOffset);
        if (count is 0 or > 8) throw new InvalidDataException("NEIGHBOR_COUNT");
        references = new uint[count];
        for (int index = 0; index < references.Length; ++index)
            references[index] = CrashOctree.U32(ram, header + NeighborOffset + (uint)index * 4);
        for (int axis = 0; axis < 3; ++axis)
        {
            input[axis] = unchecked((int)CrashOctree.U32(ram, vector + (uint)axis * 4));
            long minimum = (long)input[axis] - (axis == 1 ? 68480 : 76800);
            long maximum = (long)input[axis] + (axis == 1 ? 238720 : 76800);
            if (minimum < int.MinValue || maximum > int.MaxValue)
                throw new InvalidDataException("QUERY_RANGE");
            low[axis] = (int)minimum; high[axis] = (int)maximum;
        }
    }
    private void CheckScene(ReadOnlySpan<byte> ram)
    {
        if (CrashOctree.U32(ram, 0x80056710) != 9 ||
            CrashOctree.U32(ram, 0x80056400) != 0 || CrashOctree.U32(ram, 0x8005640C) != 0 ||
            CrashOctree.U32(ram, 0x800566B4) != actor ||
            CrashOctree.U32(ram, 0x80057914) != zone || CrashOctree.U32(ram, 0x8005791C) != path ||
            !CrashOctree.Fits(path, 4) || !CrashOctree.Fits(actor, 0x124) ||
            CrashOctree.U32(ram, actor) is 0 or 2)
            throw new InvalidDataException("SCENE");
    }
    private void CheckOwner(object memoryOwner, int nativeThread, long observationEpoch)
    {
        if (consumed || !ReferenceEquals(owner, memoryOwner) || thread != nativeThread || epoch != observationEpoch)
        {
            consumed = true;
            throw new InvalidDataException("STALE_OWNER_EPOCH");
        }
    }
    public void LookupStarting(ReadOnlySpan<byte> ram, object memoryOwner, int nativeThread,
        long observationEpoch, uint referenceSlot)
    {
        CheckOwner(memoryOwner, nativeThread, observationEpoch);
        consumed = true;
        CheckScene(ram);
        int index = neighbors.Count;
        if (lookupStarted || index >= references.Length ||
            referenceSlot != header + NeighborOffset + (uint)index * 4)
            throw new InvalidDataException("NEIGHBOR_ORDER");
        if (CrashOctree.U32(ram, referenceSlot) != references[index])
            throw new InvalidDataException("NEIGHBOR_REFERENCE");
        lookupStarted = true; consumed = false;
    }
    public void LookupReturned(ReadOnlySpan<byte> ram, object memoryOwner, int nativeThread,
        long observationEpoch, uint referenceSlot, uint returnedEntry)
    {
        CheckOwner(memoryOwner, nativeThread, observationEpoch);
        consumed = true;
        CheckScene(ram);
        int index = neighbors.Count;
        if (!lookupStarted || index >= references.Length || referenceSlot != header + NeighborOffset + (uint)index * 4)
            throw new InvalidDataException("NEIGHBOR_ORDER");
        CrashZoneRect source = CrashOctree.ReadRect(ram, returnedEntry);
        if (source.EntryType != 7 || ((references[index] & 1) != 0 && references[index] != source.Eid))
            throw new InvalidDataException("NEIGHBOR_IDENTITY");
        bool intersects = true;
        for (int axis = 0; axis < 3; ++axis)
            intersects &= source.Min[axis] < high[axis] && source.Max[axis] >= low[axis];
        neighbors.Add(new CrashQueryNeighbor(referenceSlot, references[index],
            CrashOctree.U32(ram, referenceSlot), source, intersects, Array.Empty<CrashQueryNode>()));
        lookupStarted = false; consumed = false;
    }
    public CrashQueryReceipt Complete(ReadOnlySpan<byte> ram, object memoryOwner, int nativeThread,
        long observationEpoch, uint returnedCount)
    {
        CheckOwner(memoryOwner, nativeThread, observationEpoch);
        consumed = true;
        CheckScene(ram);
        CrashZoneRect currentZone = CrashOctree.ReadRect(ram, zone);
        if (currentZone.RectAddress != zoneSource.RectAddress || currentZone.RectEnd != zoneSource.RectEnd ||
            currentZone.Eid != zoneSource.Eid || currentZone.EntryType != 7 ||
            currentZone.Digest != zoneSource.Digest || CrashOctree.U32(ram, zone + 16) != header ||
            CrashOctree.U32(ram, header + NeighborCountOffset) != references.Length ||
            lookupStarted || neighbors.Count != references.Length)
            throw new InvalidDataException("NEIGHBOR_COVERAGE");
        uint count = CrashOctree.U32(ram, query + CountOffset);
        if (count >= 512 || returnedCount != count || CrashOctree.U32(ram, query + 0x1000) != 1)
            throw new InvalidDataException("QUERY_COUNT");
        if (CrashOctree.U32(ram, query + count * 8) != uint.MaxValue)
            throw new InvalidDataException("QUERY_SENTINEL");
        for (int axis = 0; axis < 3; ++axis)
            if (unchecked((int)CrashOctree.U32(ram, query + BoundOffset + (uint)axis * 4)) != low[axis] ||
                unchecked((int)CrashOctree.U32(ram, query + BoundOffset + 12 + (uint)axis * 4)) != high[axis])
                throw new InvalidDataException("QUERY_BOUND");
        return Decode(ram, (int)count);
    }
    // Diagnostic-only bounded trailer witness. Never authorizes colliders or
    // bypasses Complete()'s original sentinel/owner/source validation.
    public string DescribeTrailer(ReadOnlySpan<byte> ram, object memoryOwner,
        int nativeThread, long observationEpoch)
    {
        if (!ReferenceEquals(owner, memoryOwner) || thread != nativeThread ||
            epoch != observationEpoch || ram.Length != CrashOctree.RamSize)
            return "STALE_OR_UNOWNED";
        if (!CrashOctree.Fits(query, QuerySize))
            return "INVALID_QUERY";
        uint count = CrashOctree.U32(ram, query + CountOffset);
        if (count >= 512)
            return "COUNT_OUT_OF_RANGE";
        uint first = CrashOctree.U32(ram, query + count * 8);
        uint second = CrashOctree.U32(ram, query + count * 8 + 4);
        uint prior = count > 0 ? CrashOctree.U32(ram, query + (count - 1) * 8) : 0;
        return $"count={count} trailer_first=0x{first:X8} trailer_second=0x{second:X8} previous_first=0x{prior:X8}";
    }

    private CrashQueryReceipt Decode(ReadOnlySpan<byte> ram, int count)
    {
        int cursor = 0;
        var decoded = new List<CrashQueryNeighbor>();
        foreach (CrashQueryNeighbor neighbor in neighbors)
        {
            CrashZoneRect source = CrashOctree.ReadRect(ram, neighbor.Source.Entry);
            if (source.Eid != neighbor.Source.Eid || source.EntryType != 7 ||
                source.RectAddress != neighbor.Source.RectAddress || source.RectEnd != neighbor.Source.RectEnd ||
                source.Digest != neighbor.Source.Digest ||
                CrashOctree.U32(ram, neighbor.Slot) != neighbor.ReferenceAfter)
                throw new InvalidDataException("NEIGHBOR_CHANGED");
            if (!neighbor.Intersects) { decoded.Add(neighbor); continue; }
            decoded.Add(DecodeNeighbor(ram, count, neighbor, ref cursor));
        }
        if (cursor != count) throw new InvalidDataException("UNBOUND_RESULTS");
        return new CrashQueryReceipt(epoch, query, actor, zone, path, input, low, high, count, decoded.ToArray());
    }
    private CrashQueryNeighbor DecodeNeighbor(ReadOnlySpan<byte> ram, int count,
        CrashQueryNeighbor neighbor, ref int cursor)
    {
        CrashZoneRect source = neighbor.Source;
        if (cursor + 2 > count || Half(ram, query + (uint)cursor * 8) != 0)
            throw new InvalidDataException("DESCRIPTOR");
        for (int axis = 0; axis < 3; ++axis)
        {
            int dimension = (source.Max[axis] - source.Min[axis]) / 256;
            if (dimension > short.MaxValue || source.Depths[axis] > 7 ||
                Half(ram, query + (uint)cursor * 8 + 2 + (uint)axis * 2) != dimension ||
                Half(ram, query + (uint)cursor * 8 + 10 + (uint)axis * 2) != source.Depths[axis])
                throw new InvalidDataException("DESCRIPTOR_SOURCE");
        }
        cursor += 2;
        var nodes = new List<CrashQueryNode>();
        while (cursor < count && Half(ram, query + (uint)cursor * 8) != 0)
        {
            uint address = query + (uint)cursor * 8;
            ushort compact = unchecked((ushort)Half(ram, address));
            if (compact == ushort.MaxValue) throw new InvalidDataException("EARLY_SENTINEL");
            int depth = compact & 7;
            if (depth > Math.Max(source.Depths[0], Math.Max(source.Depths[1], source.Depths[2])))
                throw new InvalidDataException("COMPACT_DEPTH");
            int[] relative = new int[3], minimum = new int[3], maximum = new int[3];
            for (int axis = 0; axis < 3; ++axis)
            {
                relative[axis] = Half(ram, address + 2 + (uint)axis * 2);
                long start = low[axis] + (long)relative[axis] * 16;
                long end = start + ((source.Max[axis] - source.Min[axis]) >> Math.Min(depth, source.Depths[axis]));
                if (start < (long)source.Min[axis] - 15 || end > source.Max[axis] || end <= start)
                    throw new InvalidDataException("COMPACT_RANGE");
                minimum[axis] = checked((int)start); maximum[axis] = checked((int)end);
            }
            nodes.Add(new CrashQueryNode(compact, ((compact >> 3) << 1) | 1, depth,
                relative, minimum, maximum));
            ++cursor;
        }
        // The pinned producer emits no leaf for root 0, and exactly one
        // level-zero leaf for an odd root. Stable source bytes alone do not
        // establish that decoded rows came from that source.
        ushort root = unchecked((ushort)Half(ram, source.RectAddress + 28));
        if (root == 0)
        {
            if (nodes.Count != 0) throw new InvalidDataException("ROOT_RESULT");
        }
        else if ((root & 1) != 0)
        {
            // The source result has a 13-bit node field; zero compact words
            // alias descriptors. Do not claim an unambiguous reconstructed ID.
            if (root == 1 || (root >> 1) > 0x1FFF)
                throw new InvalidDataException("ROOT_ENCODING");
            if (nodes.Count != 1 || nodes[0].Depth != 0 ||
                nodes[0].ReconstructedNode != root)
                throw new InvalidDataException("ROOT_RESULT");
            for (int axis = 0; axis < 3; ++axis)
            {
                long delta = (long)source.Min[axis] - low[axis];
                long relative = delta >> 4; // producer's arithmetic fixed-point shift
                if (delta < int.MinValue || delta > int.MaxValue ||
                    relative < short.MinValue || relative > short.MaxValue ||
                    nodes[0].Relative16[axis] != relative)
                    throw new InvalidDataException("ROOT_RESULT");
            }
        }
        // Internal-root traversal membership is NOT certified here. All
        // receipt surface/frame/lifetime/material authorization remains false.
        return neighbor with { Nodes = nodes.ToArray() };
    }
    private static short Half(ReadOnlySpan<byte> ram, uint address)
    {
        if (ram.Length != CrashOctree.RamSize || (address & 1) != 0 || !CrashOctree.Fits(address, 2))
            throw new InvalidDataException("RAM_ADDRESS");
        return BinaryPrimitives.ReadInt16LittleEndian(ram.Slice((int)(address - CrashOctree.Base), 2));
    }
}
