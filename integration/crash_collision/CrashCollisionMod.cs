using System;
using System.IO;
using System.Text.Json;
using RecompOne.Runtime.Events;
using RecompOne.Runtime.Hardware;
using RecompOne.Runtime.Memory;
using RecompOne.Runtime.Modding;

public sealed class CrashCollisionMod : IMod
{
    private bool armed, valid;
    private long started, next, last;
    private int sequence, epoch;
    private string scope;
    private PSMemory memory;
    public void OnLoad()
    {
        if (Environment.GetEnvironmentVariable("CM64_COLLISION_PROBE") != "1") return;
        armed = true; started = Environment.TickCount64; next = started; last = started;
        Event.AddListener<PadReadEvent>(OnPad);
        Console.WriteLine("[cm64-collision] ARMED read_only=true phase=PAD_UNKNOWN triangles=false");
    }
    public void OnUnload()
    {
        Event.RemoveListener<PadReadEvent>(OnPad);
        armed = valid = false; memory = null;
    }
    private void OnPad(PadReadEvent eventData)
    {
        if (!armed || eventData.Port != 0) return;
        long now = Environment.TickCount64;
        if (now - started > 90000 || sequence >= 24) { OnUnload(); return; }
        bool gap = now - last > 250; last = now;
        if (gap) valid = false;
        try
        {
            if (eventData.Memory is not PSMemory current || current.Ram.Length != CrashOctree.RamSize)
            { valid = false; return; }
            ReadOnlySpan<byte> ram = current.Ram;
            uint level = CrashOctree.U32(ram, 0x80056710);
            if (level != 9 || CrashOctree.U32(ram, 0x80056400) != 0 ||
                CrashOctree.U32(ram, 0x8005640C) != 0 || (eventData.Buttons & Controller.Start) == 0)
            { valid = false; return; }
            uint zone = CrashOctree.U32(ram, 0x80057914), path = CrashOctree.U32(ram, 0x8005791C);
            uint actor = CrashOctree.U32(ram, 0x800566B4);
            if (!CrashOctree.Fits(path, 4) || !CrashOctree.Fits(actor, 0x124) ||
                CrashOctree.U32(ram, actor) is 0 or 2)
            { valid = false; return; }
            uint actorZone = CrashOctree.U32(ram, actor + 0x28);
            string identity = $"{level}:{zone}:{path}:{actor}:{actorZone}";
            if (memory != current || scope == null || !scope.StartsWith(identity + ":", StringComparison.Ordinal))
                valid = false;
            if (now < next) return;
            next = now + 1000;
            CrashZone decoded = CrashOctree.Read(ram, zone);
            string newScope = identity + ":" + decoded.Eid + ":" + decoded.Digest;
            if (!valid || scope != newScope) ++epoch;
            scope = newScope; memory = current; valid = true;
            int[] position = { unchecked((int)CrashOctree.U32(ram, actor + 0x80)),
                unchecked((int)CrashOctree.U32(ram, actor + 0x84)),
                unchecked((int)CrashOctree.U32(ram, actor + 0x88)) };
            Console.WriteLine("CM64_COLLISION " + JsonSerializer.Serialize(new {
                version = 1, sequence = ++sequence, epoch, level, path, actor, actorZone,
                position, source = "C1_ZONE_ITEM1", phase = "PAD_UNKNOWN",
                launcherPin = "224da7757920a817de2d9242416f657ab95782ea",
                c1Pin = "256fdcef59f15a190290cc19db3fa9a707843b69",
                zone = decoded, originalQueryCorrelated = false, allocationGenerationKnown = false,
                neighborCoverage = false, materialMappingKnown = false, triangles = false
            }));
        }
        catch (Exception error)
        {
            valid = false;
            if (now >= next) next = now + 1000;
            if (error is not InvalidDataException) OnUnload();
            Console.WriteLine("[cm64-collision] REJECT reason=" + error.GetType().Name + ":" + error.Message);
        }
    }
}
