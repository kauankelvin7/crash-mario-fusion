using System;
using System.Buffers.Binary;
using System.IO;
using System.Linq;

public static class QueryTests
{
    private const uint Base = CrashOctree.Base;
    private static int checks;
    private static void Put32(byte[] ram, int offset, uint value) =>
        BinaryPrimitives.WriteUInt32LittleEndian(ram.AsSpan(offset, 4), value);
    private static void Put16(byte[] ram, int offset, int value) =>
        BinaryPrimitives.WriteUInt16LittleEndian(ram.AsSpan(offset, 2), unchecked((ushort)value));
    private static byte[] Fixture()
    {
        var ram = new byte[CrashOctree.RamSize];
        for (int index = 0; index < 3; ++index)
        {
            int entry = 0x100 + index * 0x500, header = entry + 0x100, rect = entry + 0x400;
            Put32(ram, entry, 0x100FFFF); Put32(ram, entry + 4, (uint)(101 + index * 2));
            Put32(ram, entry + 8, 7); Put32(ram, entry + 12, 2);
            Put32(ram, entry + 16, Base + (uint)header);
            Put32(ram, entry + 20, Base + (uint)rect); Put32(ram, entry + 24, Base + (uint)rect + 64);
            Put32(ram, rect, unchecked((uint)(index == 0 ? -32 : index == 2 ? 3000 : 0)));
            Put32(ram, rect + 4, (uint)(index == 1 ? 16 : 0));
            for (int axis = 0; axis < 3; ++axis) Put32(ram, rect + 12 + axis * 4, 64);
            Put16(ram, rect + 28, 3);
            Put32(ram, 0x414 + index * 4, (uint)(101 + index * 2));
        }
        Put32(ram, 0x410, 3); Put32(ram, 0x1200, 1);
        Put32(ram, 0x566B4, Base + 0x1200);
        Put32(ram, 0x57914, Base + 0x100);
        Put32(ram, 0x5791C, Base + 0x1400);
        Put32(ram, 0x56710, 9);
        Put32(ram, 0x3000, 1); Put32(ram, 0x3004, 6);
        int[] low = { -76800, -68480, -76800 }, high = { 76800, 238720, 76800 };
        for (int axis = 0; axis < 3; ++axis)
        {
            Put32(ram, 0x3008 + axis * 4, unchecked((uint)low[axis]));
            Put32(ram, 0x3014 + axis * 4, (uint)high[axis]);
        }
        for (int index = 0; index < 2; ++index)
        {
            int descriptor = 0x2000 + index * 24;
            for (int axis = 0; axis < 3; ++axis) Put16(ram, descriptor + 2 + axis * 2, 64);
            Put16(ram, descriptor + 16, 8);
            Put16(ram, descriptor + 18, index == 0 ? 4288 : 4800);
            Put16(ram, descriptor + 20, index == 0 ? 4280 : 4536);
            Put16(ram, descriptor + 22, 4800);
        }
        Put32(ram, 0x2030, uint.MaxValue);
        return ram;
    }
    private static CrashNativeQuery Begin(byte[] ram, object owner) =>
        new(ram, owner, 1, 1, Base + 0x1500, Base + 0x1200, Base + 0x2000);
    private static CrashNativeQuery Observed(byte[] ram, object owner)
    {
        CrashNativeQuery query = Begin(ram, owner);
        for (int index = 0; index < 3; ++index)
        {
            query.LookupStarting(ram, owner, 1, 1, Base + 0x414 + (uint)index * 4);
            query.LookupReturned(ram, owner, 1, 1, Base + 0x414 + (uint)index * 4,
                Base + 0x100 + (uint)index * 0x500);
        }
        return query;
    }
    private static void RejectResult(Action<byte[]> mutate, string reason)
    {
        byte[] ram = Fixture(); object owner = new();
        CrashNativeQuery query = Observed(ram, owner); mutate(ram);
        Reject(() => query.Complete(ram, owner, 1, 1, CrashOctree.U32(ram, Base + 0x3004)), reason);
    }
    public static void Main(string[] args)
    {
        byte[] ram = Fixture(); object owner = new();
        if (args.Length == 1 && args[0] == "--oracle")
        {
            byte[] bytes = Convert.FromHexString(Console.In.ReadToEnd().Trim());
            Check(bytes.Length == CrashNativeQuery.QuerySize);
            bytes.CopyTo(ram, 0x2000);
        }
        byte[] before = (byte[])ram.Clone();
        CrashNativeQuery query = Observed(ram, owner);
        CrashQueryReceipt receipt = query.Complete(ram, owner, 1, 1, 6);
        Check(ram.SequenceEqual(before));
        Check(receipt.ResultCount == 6 && receipt.Neighbors.Length == 3);
        Check(receipt.Neighbors.Select(neighbor => neighbor.Intersects).SequenceEqual(new[] { true, true, false }));
        Check(receipt.Neighbors[0].Nodes[0].Min.SequenceEqual(new[] { -8192, 0, 0 }));
        Check(receipt.Neighbors[1].Nodes[0].Max.SequenceEqual(new[] { 16384, 20480, 16384 }));
        Check(!receipt.SurfacesAllowed && !receipt.AllocationGenerationKnown && !receipt.NativeFrameKnown);
        Check(query.DescribeTrailer(ram, owner, 1, 1).Contains("trailer_first=0xFFFFFFFF"));
        Check(query.DescribeTrailer(ram, new object(), 1, 1) == "STALE_OR_UNOWNED");
        Check(query.DescribeTrailer(ram, owner, 2, 1) == "STALE_OR_UNOWNED");
        Check(query.DescribeTrailer(ram, owner, 1, 2) == "STALE_OR_UNOWNED");
        byte[] alteredTrailer = (byte[])ram.Clone();
        Put32(alteredTrailer, 0x2030, 0x12345678);
        Check(query.DescribeTrailer(alteredTrailer, owner, 1, 1).Contains("trailer_first=0x12345678"));
        Reject(() => query.Complete(ram, owner, 1, 1, 6), "STALE_OWNER_EPOCH");
        NegativeChecks();
        Console.WriteLine("VERIFIED_SYNTHETIC native_query_checks=" + checks + " games=false surfaces=false");
    }
    private static void NegativeChecks()
    {
        RejectResult(ram => Put32(ram, 0x3004, 512), "QUERY_COUNT");
        RejectResult(ram => Put32(ram, 0x3004, uint.MaxValue), "QUERY_COUNT");
        RejectResult(ram => Put32(ram, 0x3000, 0), "QUERY_COUNT");
        RejectResult(ram => Put32(ram, 0x2030, 0), "QUERY_SENTINEL");
        RejectResult(ram => Put32(ram, 0x3008, 0), "QUERY_BOUND");
        RejectResult(ram => Put16(ram, 0x2000, 8), "DESCRIPTOR");
        RejectResult(ram => Put16(ram, 0x2002, 65), "DESCRIPTOR_SOURCE");
        RejectResult(ram => Put16(ram, 0x200A, 1), "DESCRIPTOR_SOURCE");
        RejectResult(ram => Put16(ram, 0x2010, -1), "EARLY_SENTINEL");
        RejectResult(ram => Put16(ram, 0x2012, 0), "COMPACT_RANGE");
        RejectResult(ram => Put16(ram, 0x2010, 9), "COMPACT_DEPTH");
        RejectResult(ram => Put32(ram, 0x56710, 8), "SCENE");
        RejectResult(ram => Put32(ram, 0x56400, 1), "SCENE");
        RejectResult(ram => Put32(ram, 0x5640C, 1), "SCENE");
        RejectResult(ram => Put32(ram, 0x566B4, Base + 0x1600), "SCENE");
        RejectResult(ram => Put32(ram, 0x5791C, Base + 0x1600), "SCENE");
        RejectResult(ram => Put32(ram, 0x410, 2), "NEIGHBOR_COVERAGE");
        RejectResult(ram => Put32(ram, 0x418, 999), "NEIGHBOR_CHANGED");
        RejectResult(ram => Put32(ram, 0x608, 1), "NEIGHBOR_CHANGED");
        RejectResult(ram => Put16(ram, 0xA1C, 19), "NEIGHBOR_CHANGED");
        RejectResult(ram => {
            Buffer.BlockCopy(ram, 0xA00, ram, 0xA80, 64);
            Put32(ram, 0x614, Base + 0xA80); Put32(ram, 0x618, Base + 0xAC0);
        }, "NEIGHBOR_CHANGED");
        OwnershipChecks();
    }
    private static void OwnershipChecks()
    {
        byte[] ram = Fixture(); object owner = new();
        for (int variant = 0; variant < 3; ++variant)
        {
            CrashNativeQuery query = Observed(ram, owner);
            int selected = variant;
            Reject(() => query.Complete(ram, selected == 0 ? new object() : owner,
                selected == 1 ? 2 : 1, selected == 2 ? 2 : 1, 6), "STALE_OWNER_EPOCH");
            Reject(() => query.Complete(ram, owner, 1, 1, 6), "STALE_OWNER_EPOCH");
        }
        CrashNativeQuery missing = Begin(ram, owner);
        Reject(() => missing.Complete(ram, owner, 1, 1, 6), "NEIGHBOR_COVERAGE");
        CrashNativeQuery reordered = Begin(ram, owner);
        Reject(() => reordered.LookupStarting(ram, owner, 1, 1, Base + 0x418), "NEIGHBOR_ORDER");
        Reject(() => reordered.Complete(ram, owner, 1, 1, 6), "STALE_OWNER_EPOCH");
        CrashNativeQuery identity = Begin(ram, owner);
        identity.LookupStarting(ram, owner, 1, 1, Base + 0x414);
        Reject(() => identity.LookupReturned(ram, owner, 1, 1, Base + 0x414, Base + 0x600), "NEIGHBOR_IDENTITY");
        Reject(() => new CrashNativeQuery(ram, owner, 1, 1, Base + 0x1500,
            Base + 0x1600, Base + 0x2000), "QUERY_ARGUMENT");
        Put32(ram, 0x1500, int.MaxValue);
        Reject(() => Begin(ram, owner), "QUERY_RANGE");
        ram = Fixture(); Put32(ram, 0x410, 9);
        Reject(() => Begin(ram, owner), "NEIGHBOR_COUNT");
        ram = Fixture(); Put16(ram, 0xA1C, 19); Put16(ram, 0x2028, 72);
        CrashQueryReceipt eventNode = Observed(ram, owner).Complete(ram, owner, 1, 1, 6);
        Check(eventNode.Neighbors[1].Nodes[0].ReconstructedNode == 19 && !eventNode.MaterialMappingKnown);
        PairAndEmptyChecks();
    }
    private static void PairAndEmptyChecks()
    {
        byte[] ram = Fixture(); object owner = new();
        CrashNativeQuery altered = Begin(ram, owner);
        Put32(ram, 0x414, 103);
        Reject(() => altered.LookupStarting(ram, owner, 1, 1, Base + 0x414), "NEIGHBOR_REFERENCE");
        ram = Fixture(); CrashNativeQuery unpaired = Begin(ram, owner);
        Reject(() => unpaired.LookupReturned(ram, owner, 1, 1, Base + 0x414, Base + 0x100), "NEIGHBOR_ORDER");
        ram = Fixture(); CrashNativeQuery nested = Begin(ram, owner);
        nested.LookupStarting(ram, owner, 1, 1, Base + 0x414);
        Reject(() => nested.LookupStarting(ram, owner, 1, 1, Base + 0x414), "NEIGHBOR_ORDER");
        ram = Fixture(); CrashNativeQuery incomplete = Begin(ram, owner);
        incomplete.LookupStarting(ram, owner, 1, 1, Base + 0x414);
        Reject(() => incomplete.Complete(ram, owner, 1, 1, 6), "NEIGHBOR_COVERAGE");
        ram = Fixture();
        Put32(ram, 0x3004, 4);
        Buffer.BlockCopy(ram, 0x2018, ram, 0x2010, 16);
        Put32(ram, 0x2020, uint.MaxValue);
        CrashQueryReceipt empty = Observed(ram, owner).Complete(ram, owner, 1, 1, 4);
        Check(empty.Neighbors.All(neighbor => neighbor.Nodes.Length == 0) && !empty.SurfacesAllowed);
        ram = Fixture(); Put16(ram, 0x51C, 36);
        Check(CrashOctree.ReadRect(ram, Base + 0x100).RectAddress == Base + 0x500);
    }
    private static void Check(bool condition)
    {
        if (!condition) throw new Exception("Query assertion " + checks);
        ++checks;
    }
    private static void Reject(Action action, string reason)
    {
        try { action(); }
        catch (InvalidDataException error) { Check(error.Message == reason); return; }
        throw new Exception("Expected rejection: " + reason);
    }
}
