using System;
using System.Buffers.Binary;
using System.Collections.Generic;
using System.Diagnostics;
using System.Text.Json;
using RecompOne.Runtime.Catalogs;
using RecompOne.Runtime.Host.Cheats;
using RecompOne.Runtime.Context;
using RecompOne.Runtime.Memory;

namespace RecompOne.Runtime;

public static class CrashWorldSourceProbe
{
    const uint WorldCall = 0x80019508;
    const uint ZoneAddress = 0x80057914, PathAddress = 0x8005791C, DrawAddress = 0x80057960;
    static readonly bool Enabled = Environment.GetEnvironmentVariable("CM64_WORLD_SOURCE_PROBE") == "1";
    static readonly long Started = Stopwatch.GetTimestamp();
    static long lastSample, lastAttempt;
    static int samples, epoch, generation;
    static int debugWorldCalls, debugOtCalls, debugRtptCalls;
    static uint clearedOt, previousLevel, previousZone, previousPath, previousDraw;
    static uint guestOtDraw = uint.MaxValue;
    static bool stopped;
    static bool warpRequested;
    static Scope? active;

    sealed class Scope
    {
        public required CpuContext Cpu;
        public required PSMemory Memory;
        public uint Level, Zone, Path, Draw, Ot;
        public int Generation;
        public string OtSource = "UNKNOWN";
        public Sample? Candidate;
    }

    sealed class Sample
    {
        public uint World, WorldKey, Header, Polygon, Primitive, ZoneHeader, Descriptor, PolyId;
        public uint WorldCount, PolyIdAddress, PolyIdWord;
        public uint[] DescriptorWords = [], HeaderWords = [];
        public uint[] PolygonWords = [], VertexAddresses = [], VertexWords = [];
        public int[] Xyz = [], Rotation = [], Translation = [], Origin = [], CameraTranslation = [];
        public uint H;
        public int Ofx, Ofy;
        public uint[] Sxy = [], Z = [];
        public uint Flag;
    }

    static bool Live => Enabled && !stopped && samples < 24 &&
        Stopwatch.GetElapsedTime(Started).TotalSeconds <= 90;
    static uint Physical(uint address) => address & 0x1FFFFFFF;
    static bool Fits(uint address, int bytes) =>
        (address >> 29 == 0 || address >> 29 == 4 || address >> 29 == 5) &&
        Physical(address) <= 0x200000u - (uint)bytes && (address & 3) == 0;
    static uint Word(PSMemory memory, uint address)
    {
        if (!Fits(address, 4) || memory.Ram.Length != 0x200000)
            throw new InvalidOperationException("RAM span rejected");
        return BinaryPrimitives.ReadUInt32LittleEndian(memory.Ram.Slice((int)Physical(address), 4));
    }
    static uint Scratch(PSMemory memory, int offset) =>
        BinaryPrimitives.ReadUInt32LittleEndian(memory.CM64Scratchpad.Slice(offset, 4));
    static short Signed(uint value) => unchecked((short)value);
    static void Disable() { stopped = true; active = null; }

    public static void OrderingTable(uint last, uint count)
    {
        if (!Live) return;
        try
        {
            if (Environment.GetEnvironmentVariable("CM64_WORLD_SOURCE_DEBUG") == "1" && debugOtCalls++ < 3)
                Console.WriteLine($"[cm64-world-gate] OT_VISIT count={count} last={last:X8} generation={generation}");
            active = null;
            generation++;
            clearedOt = 0;
            if (count == 2048 && Physical(last) >= 8188 && Fits(last, 4))
                clearedOt = Physical(last) - 8188;
        }
        catch { Disable(); }
    }

    // Pinned c1 src/psx/r3000a.s RGpuResetOT writes 2047 forward
    // 24-bit pointers followed by the 0xFFFFFF end tag. The original
    // retail executable uses that guest routine, not necessarily DMA6.
    // Verify all 2048 source-owned RAM tags BEFORE world geometry modifies OT.
    static bool OriginalGuestOtReset(PSMemory ram, uint pointer)
    {
        if (!Fits(pointer, 8192)) return false;
        uint baseAddress = Physical(pointer);
        for (uint index = 0; index < 2047; ++index)
        {
            if (Word(ram, pointer + index * 4) != ((baseAddress + (index + 1) * 4) & 0xFFFFFF))
                return false;
        }
        return Word(ram, pointer + 8188) == 0x00FFFFFF;
    }

    public static void Enter(uint address, CpuContext cpu, IMemory memory)
    {
        // Dispatcher enters for regular guest calls before the level is loaded;
        // the OT callback itself does not run at the title screen. Request only
        // the official host developer-menu warp, once, in a private opt-in run.
        if (Enabled && !warpRequested && Environment.GetEnvironmentVariable("CM64_WORLD_WARP_SANITY") == "1")
        {
            warpRequested = true;
            CheatManager.RequestWarp(9, 1);
            Console.WriteLine("[cm64-world-warp] ORIGINAL_HOST_WARP_REQUESTED level=9 map_slot=1 authenticated=false");
        }
        if (Environment.GetEnvironmentVariable("CM64_WORLD_SOURCE_DEBUG") == "1" && address == WorldCall && debugWorldCalls++ < 3)
            Console.WriteLine($"[cm64-world-gate] WORLD_CALL_ENTER gen={generation} ot={clearedOt:X8} a0={cpu.A0:X8} live={Live}");
        if (address != WorldCall || !Live) return;
        try
        {
            if (active != null) { Disable(); return; }
            if (lastAttempt != 0 && Stopwatch.GetElapsedTime(lastAttempt).TotalMilliseconds < 900) return;
            lastAttempt = Stopwatch.GetTimestamp();
            if (memory is not PSMemory ram || ram.Ram.Length != 0x200000 ||
                !Fits(cpu.A0, 8192)) return;
            uint level = Word(ram, Catalog.LevelIdAddr);
            if (!Catalog.Levels.TryGet(level, out var info) || info.Kind != LevelKind.Gameplay ||
                Word(ram, 0x80056400) != 0 || Word(ram, 0x8005640C) != 0) return;
            uint zone = Word(ram, ZoneAddress), path = Word(ram, PathAddress), draw = Word(ram, DrawAddress);
            if (generation == 0 || (guestOtDraw != uint.MaxValue && guestOtDraw != draw))
            {
                if (!OriginalGuestOtReset(ram, cpu.A0)) return;
                generation++;
                clearedOt = Physical(cpu.A0);
                guestOtDraw = draw;
            }
            if (Physical(cpu.A0) != clearedOt) return;
            if (!Fits(zone, 20) || !Fits(path, 4) || Word(ram, zone) != 0x0100FFFF) return;
            if (samples == 0 || level != previousLevel || zone != previousZone || path != previousPath ||
                draw <= previousDraw || (lastSample != 0 && Stopwatch.GetElapsedTime(lastSample).TotalSeconds > 2)) epoch++;
            active = new Scope { Cpu = cpu, Memory = ram, Level = level, Zone = zone,
                Path = path, Draw = draw, Ot = cpu.A0, Generation = generation,
                OtSource = guestOtDraw == uint.MaxValue ? "DMA6_CLEAR" : "GUEST_RGPU_RESET_CHAIN" };
        }
        catch { Disable(); }
    }

    public static void BeforeGte(uint command)
    {
        if (command == 0x4A280030 && Environment.GetEnvironmentVariable("CM64_WORLD_SOURCE_DEBUG") == "1" && debugRtptCalls++ < 3)
            Console.WriteLine($"[cm64-world-gate] RTPT_ENTER active={active != null} live={Live} candidate={active?.Candidate != null}");
        if (!Live || active == null || active.Candidate != null || command != 0x4A280030) return;
        try
        {
            var scope = active;
            var cpu = scope.Cpu;
            var memory = scope.Memory;
            uint world = cpu.T4, zoneHeader = Word(memory, scope.Zone + 16);
            uint worldCount = Word(memory, zoneHeader);
            if (worldCount > 8 || world >= worldCount) return;
            int scratch = checked(0x100 + (int)world * 64);
            uint descriptor = zoneHeader + 4 + world * 64;
            for (uint offset = 0; offset < 32; offset += 4)
                if (Scratch(memory, scratch + (int)offset) != Word(memory, descriptor + offset)) return;
            uint header = Scratch(memory, scratch + 16);
            uint polygons = Scratch(memory, scratch + 20), vertices = Scratch(memory, scratch + 24);
            if (polygons != cpu.S7 || vertices != cpu.T8 || !Fits(header, 32) ||
                !Fits(polygons, 8) || !Fits(vertices, 8) ||
                Word(memory, header + 28) != 0) return;
            uint idAddress = cpu.T2 + 2;
            uint idWord = Word(memory, idAddress & ~3u);
            uint id = (idWord >> ((int)(idAddress & 2) * 8)) & 0xFFFF;
            if ((idAddress & 1) != 0 || (id >> 12) != world ||
                (id & 0xFFF) >= Word(memory, header + 12)) return;
            uint polygon = polygons + (id & 0xFFF) * 8;
            uint first = Word(memory, polygon), second = Word(memory, polygon + 4);
            uint[] offsets = [(second >> 17) & 0x7FF8, (second >> 5) & 0x7FF8, (first >> 17) & 0x7FF8];
            var sample = new Sample { World = world, WorldKey = Word(memory, descriptor), Header = header,
                Polygon = polygon, Primitive = cpu.T3, PolygonWords = [first, second],
                ZoneHeader = zoneHeader, Descriptor = descriptor, PolyId = id,
                WorldCount = worldCount, PolyIdAddress = idAddress, PolyIdWord = idWord,
                DescriptorWords = new uint[8], HeaderWords = new uint[8],
                VertexAddresses = new uint[3], VertexWords = new uint[6], Xyz = new int[9],
                Rotation = new int[9], Translation = new int[3], Origin = new int[3], CameraTranslation = new int[3] };
            if (!Fits(cpu.T3, 40) || Physical(cpu.T3) < Physical(scope.Ot) + 8192 &&
                Physical(cpu.T3) + 40 > Physical(scope.Ot)) return;
            for (int index = 0; index < 8; index++)
            {
                sample.DescriptorWords[index] = Word(memory, descriptor + (uint)index * 4);
                sample.HeaderWords[index] = Word(memory, header + (uint)index * 4);
            }
            for (int index = 0; index < 3; index++)
            {
                if (offsets[index] / 8 >= Word(memory, header + 16)) return;
                uint vertex = vertices + offsets[index];
                uint low = Word(memory, vertex), high = Word(memory, vertex + 4), zBits = high & 0x70006;
                int[] xyz = [Signed(high & 0xFFF8), Signed((high >> 16) & 0xFFF8),
                    Signed(((low >> 24) << 3) | (zBits << 10) | (zBits >> 3))];
                uint xy = Gte.Read(index * 2);
                if (xyz[0] != Signed(xy) || xyz[1] != Signed(xy >> 16) || xyz[2] != Signed(Gte.Read(index * 2 + 1))) return;
                sample.VertexAddresses[index] = vertex;
                sample.VertexWords[index * 2] = low; sample.VertexWords[index * 2 + 1] = high;
                Array.Copy(xyz, 0, sample.Xyz, index * 3, 3);
                sample.Translation[index] = unchecked((int)Gte.ReadControl(5 + index));
                if (sample.Translation[index] != unchecked((int)Scratch(memory, scratch + 4 + index * 4))) return;
                sample.Origin[index] = unchecked((int)Word(memory, header + (uint)index * 4));
                sample.CameraTranslation[index] = unchecked((int)Word(memory, 0x80057864 + (uint)index * 4));
            }
            for (int index = 0; index < 9; index++)
            {
                sample.Rotation[index] = Signed(Gte.ReadControl(index / 2) >> ((index % 2) * 16));
                uint address = 0x800577E4 + (uint)index * 2;
                int original = Signed(Word(memory, address & ~3u) >> ((int)(address & 2) * 8));
                if (sample.Rotation[index] != original) return;
            }
            sample.H = Gte.ReadControl(26) & 0xFFFF;
            sample.Ofx = unchecked((int)Gte.ReadControl(24)); sample.Ofy = unchecked((int)Gte.ReadControl(25));
            scope.Candidate = sample;
        }
        catch { Disable(); }
    }

    public static void AfterGte(uint command)
    {
        if (command != 0x4A280030 || active?.Candidate is not Sample sample || sample.Sxy.Length != 0) return;
        try
        {
            sample.Sxy = [Gte.Read(12), Gte.Read(13), Gte.Read(14)];
            sample.Z = [Gte.Read(17), Gte.Read(18), Gte.Read(19)];
            sample.Flag = Gte.ReadControl(31);
            if (sample.Flag != 0) active.Candidate = null;
        }
        catch { Disable(); }
    }

    static List<uint[]>? FindLink(Scope scope, uint primitive)
    {
        int budget = 8192;
        for (uint slot = 0; slot < 2048 && budget > 0; slot++)
        {
            uint address = scope.Ot + slot * 4;
            var chain = new List<uint[]>();
            var seen = new HashSet<uint>();
            for (int depth = 0; depth < 128 && budget-- > 0; depth++)
            {
                if (!Fits(address, 4) || !seen.Add(Physical(address))) break;
                uint tag = Word(scope.Memory, address);
                chain.Add([address, tag]);
                if (Physical(address) == Physical(primitive)) return chain;
                uint next = tag & 0xFFFFFF;
                if (next == 0xFFFFFF) break;
                address = 0x80000000 | next;
                if (Physical(address) >= Physical(scope.Ot) && Physical(address) < Physical(scope.Ot) + 8192) break;
            }
        }
        return null;
    }

    public static void Leave(uint address, bool completed)
    {
        if (address != WorldCall || active == null) return;
        var scope = active;
        active = null;
        if (!completed) return;
        try
        {
            if (!Live || scope.Candidate is not Sample sample || sample.Sxy.Length != 3 ||
                scope.Generation != generation || Word(scope.Memory, DrawAddress) != scope.Draw ||
                Word(scope.Memory, ZoneAddress) != scope.Zone || Word(scope.Memory, PathAddress) != scope.Path ||
                Word(scope.Memory, Catalog.LevelIdAddr) != scope.Level ||
                Word(scope.Memory, 0x80056400) != 0 || Word(scope.Memory, 0x8005640C) != 0) return;
            if (Word(scope.Memory, scope.Zone) != 0x0100FFFF ||
                Word(scope.Memory, scope.Zone + 16) != sample.ZoneHeader ||
                Word(scope.Memory, sample.ZoneHeader) != sample.WorldCount ||
                Word(scope.Memory, sample.PolyIdAddress & ~3u) != sample.PolyIdWord) return;
            uint code = Word(scope.Memory, sample.Primitive + 4) >> 24;
            int[] offsets = (code & 0xFD) == 0x34 ? [8, 20, 32] : (code & 0xFD) == 0x30 ? [8, 16, 24] : [];
            if (offsets.Length != 3) return;
            if (Word(scope.Memory, sample.Polygon) != sample.PolygonWords[0] ||
                Word(scope.Memory, sample.Polygon + 4) != sample.PolygonWords[1]) return;
            for (int index = 0; index < 3; index++)
            {
                if (Word(scope.Memory, sample.Primitive + (uint)offsets[index]) != sample.Sxy[index]) return;
                if (Word(scope.Memory, sample.VertexAddresses[index]) != sample.VertexWords[index * 2] ||
                    Word(scope.Memory, sample.VertexAddresses[index] + 4) != sample.VertexWords[index * 2 + 1]) return;
            }
            for (int index = 0; index < 8; index++)
                if (Word(scope.Memory, sample.Descriptor + (uint)index * 4) != sample.DescriptorWords[index] ||
                    Word(scope.Memory, sample.Header + (uint)index * 4) != sample.HeaderWords[index]) return;
            for (int index = 0; index < 3; index++)
                if (unchecked((int)Word(scope.Memory, 0x80057864 + (uint)index * 4)) != sample.CameraTranslation[index]) return;
            for (int index = 0; index < 9; index++)
            {
                uint original = 0x800577E4 + (uint)index * 2;
                if (Signed(Word(scope.Memory, original & ~3u) >> ((int)(original & 2) * 8)) != sample.Rotation[index]) return;
            }
            var chain = FindLink(scope, sample.Primitive);
            if (chain == null) return;
            Console.WriteLine("[cm64-world] " + JsonSerializer.Serialize(new {
                schema = 2, phase = "GUEST_WORLD_RTPT_OT", sequence = samples + 1,
                source_pin = "224da7757920a817de2d9242416f657ab95782ea",
                c1_pin = "256fdcef59f15a190290cc19db3fa9a707843b69",
                level = scope.Level, zone = scope.Zone, path = scope.Path, draw = scope.Draw,
                epoch, ot_generation = generation, ot = scope.Ot, ot_source = scope.OtSource, world = sample.World,
                world_key = sample.WorldKey, header = sample.Header, origin = sample.Origin,
                zone_header = sample.ZoneHeader, world_descriptor = sample.Descriptor, poly_id = sample.PolyId,
                zone_magic = 0x0100FFFFu, world_count = sample.WorldCount,
                poly_id_address = sample.PolyIdAddress, poly_id_word = sample.PolyIdWord,
                descriptor_words = sample.DescriptorWords, header_words = sample.HeaderWords,
                polygon = sample.Polygon, polygon_words = sample.PolygonWords,
                vertex_addresses = sample.VertexAddresses, vertex_words = sample.VertexWords,
                xyz = sample.Xyz, rotation = sample.Rotation, translation = sample.Translation,
                camera_translation = sample.CameraTranslation,
                h = sample.H, ofx = sample.Ofx, ofy = sample.Ofy, command = 0x4A280030u,
                sxy = sample.Sxy, z = sample.Z, flag = sample.Flag,
                primitive = sample.Primitive, primitive_code = code, ot_chain = chain,
                postphysics = false, depth_complete = false, collision_ready = false
            }));
            samples++; lastSample = Stopwatch.GetTimestamp();
            previousLevel = scope.Level; previousZone = scope.Zone; previousPath = scope.Path; previousDraw = scope.Draw;
        }
        catch { Disable(); }
    }
}
