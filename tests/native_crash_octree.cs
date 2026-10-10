using System;
using System.Buffers.Binary;
using System.IO;
using System.Linq;

public static class OctreeTests
{
    private const uint Entry = CrashOctree.Base + 0x100;
    private const int Rect = 0x240;
    private static int checks;
    private static void Put32(byte[] ram, int offset, uint value) =>
        BinaryPrimitives.WriteUInt32LittleEndian(ram.AsSpan(offset, 4), value);
    private static void Put16(byte[] ram, int offset, ushort value) =>
        BinaryPrimitives.WriteUInt16LittleEndian(ram.AsSpan(offset, 2), value);
    private static byte[] Fixture()
    {
        var ram = new byte[CrashOctree.RamSize];
        Put32(ram, 0x100, 0x100FFFF); Put32(ram, 0x104, 123); Put32(ram, 0x108, 7);
        Put32(ram, 0x10C, 2); Put32(ram, 0x110, CrashOctree.Base + 0x200);
        Put32(ram, 0x114, CrashOctree.Base + Rect); Put32(ram, 0x118, CrashOctree.Base + Rect + 64);
        Put32(ram, Rect, unchecked((uint)-32));
        for (int axis = 0; axis < 3; ++axis) Put32(ram, Rect + 12 + axis * 4, 64);
        Put16(ram, Rect + 28, 3);
        return ram;
    }
    private static void Check(bool condition)
    {
        if (!condition) throw new Exception("Assertion " + checks);
        ++checks;
    }
    private static void Reject(Action<byte[]> mutate, string expected = null)
    {
        var ram = Fixture(); mutate(ram);
        try { CrashOctree.Read(ram, Entry); }
        catch (InvalidDataException error)
        {
            if (expected != null && error.Message != expected) throw;
            ++checks; return;
        }
        throw new Exception("Expected fail-closed decoder");
    }
    public static void Main()
    {
        var ram = Fixture(); var original = (byte[])ram.Clone();
        var zone = CrashOctree.Read(ram, Entry);
        Check(ram.SequenceEqual(original));
        Check(zone.Min.SequenceEqual(new[] { -8192, 0, 0 }));
        Check(zone.Max.SequenceEqual(new[] { 8192, 16384, 16384 }));
        Check(zone.Volumes.Length == 1 && zone.Volumes[0].Node == 3 && zone.Volumes[0].Depth == 0);
        Check(zone.Digest.Length == 64 && CrashOctree.Read(ram, Entry).Digest == zone.Digest);
        Put16(ram, Rect + 28, 36); Put16(ram, Rect + 30, 1); Put16(ram, Rect + 34, 1);
        for (int index = 0; index < 4; ++index) Put16(ram, Rect + 36 + index * 2, (ushort)(3 + index * 16));
        zone = CrashOctree.Read(ram, Entry);
        Check(zone.Volumes.Length == 4);
        Check(zone.Volumes[1].Min.SequenceEqual(new[] { -8192, 0, 8192 }));
        Check(zone.Volumes[2].Min.SequenceEqual(new[] { 0, 0, 0 }));
        Check(zone.Volumes[3].Max.SequenceEqual(new[] { 8192, 16384, 16384 }));
        Check(zone.Volumes[3].Node == 51);
        Reject(value => Put32(value, 0x100, 0));
        Reject(value => Put32(value, 0x10C, 129));
        Reject(value => Put32(value, 0x114, CrashOctree.Base + Rect + 1));
        Reject(value => Put32(value, 0x118, CrashOctree.Base + Rect + 30));
        Reject(value => Put32(value, 0x118, CrashOctree.Base + CrashOctree.RamSize + 2));
        Reject(value => Put32(value, Rect + 12, 0));
        Reject(value => Put32(value, Rect, int.MaxValue));
        Reject(value => Put32(value, Rect + 12, uint.MaxValue));
        Reject(value => Put16(value, Rect + 30, 17));
        Reject(value => Put16(value, Rect + 28, 0));
        Reject(value => Put16(value, Rect + 28, 34));
        Reject(value => { Put16(value, Rect + 28, 62); Put16(value, Rect + 30, 1); });
        Reject(value => { Put16(value, Rect + 28, 36); Put16(value, Rect + 30, 2);
            Put16(value, Rect + 36, 36); });
        Reject(value => { Put16(value, Rect + 28, 36); });
        foreach (ushort terminal in new ushort[] { 0, 3 })
            Reject(value => {
                Put32(value, 0x118, CrashOctree.Base + Rect + 128);
                Put16(value, Rect + 28, 36);
                for (int axis = 0; axis < 3; ++axis) Put16(value, Rect + 30 + axis * 2, 5);
                for (int depth = 0; depth < 5; ++depth)
                    for (int index = 0; index < 8; ++index)
                        Put16(value, Rect + 36 + depth * 16 + index * 2,
                            depth == 4 ? terminal : (ushort)(36 + (depth + 1) * 16));
            }, terminal == 0 ? "TRAVERSAL_LIMIT" : "LEAF_LIMIT");
        Check(!CrashOctree.Fits(CrashOctree.Base + CrashOctree.RamSize, 4));
        Console.WriteLine("VERIFIED_SYNTHETIC octree_checks=" + checks + " games=false");
    }
}
