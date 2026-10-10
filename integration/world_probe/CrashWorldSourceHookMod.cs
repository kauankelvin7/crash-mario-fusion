using System;
using System.Buffers.Binary;
using System.Linq;
using RecompOne.Runtime;
using RecompOne.Runtime.Context;
using RecompOne.Runtime.Dispatch;
using RecompOne.Runtime.Memory;
using RecompOne.Runtime.Modding;

// Private original-game G1 observation. Does not alter guest RAM or substitute
// the world routine; it hooks the real recompiled guest method, which may be
// invoked directly without passing through Dispatcher.Call.
public sealed class CrashWorldSourceHookMod : IMod
{
    private const uint WorldCall = 0x80019508;
    private bool armed;
    private int inspected;

    public void OnLoad()
    {
        if (Environment.GetEnvironmentVariable("CM64_WORLD_SOURCE_PROBE") != "1") return;
        var candidates = Dispatcher.Overlays.Values.Where(overlay =>
            overlay.Functions.ContainsKey(WorldCall)).ToArray();
        if (candidates.Length != 1)
        {
            Console.WriteLine("[cm64-world-gate] BLOCKED original_world_symbol_missing_or_ambiguous");
            return;
        }
        var method = candidates[0].Functions[WorldCall].Method;
        HookManager.AddPre(method, Before);
        HookManager.AddPost(method, After);
        armed = true;
        Console.WriteLine("[cm64-world-gate] ORIGINAL_WORLD_METHOD_HOOKED address=0x80019508 observational=true");
    }

    public void OnUnload() { armed = false; }

    private bool Before(CpuContext cpu, IMemory memory)
    {
        if (!armed) return true;
        if (Environment.GetEnvironmentVariable("CM64_WORLD_SOURCE_DEBUG") == "1" &&
            inspected++ < 3 && memory is PSMemory ps && ps.Ram.Length == 0x200000)
        {
            uint baseOt = cpu.A0 & 0x1FFFFFFF;
            if ((baseOt & 3) == 0 && baseOt <= 0x200000 - 8192)
            {
                var ram = ps.Ram;
                int next = 0, previous = 0, terminated = 0;
                for (uint slot = 0; slot < 2048; ++slot)
                {
                    uint value = BinaryPrimitives.ReadUInt32LittleEndian(ram.Slice((int)(baseOt + slot * 4), 4)) & 0xFFFFFF;
                    if (value == ((baseOt + slot * 4 + 4) & 0xFFFFFF)) next++;
                    if (slot > 0 && value == ((baseOt + slot * 4 - 4) & 0xFFFFFF)) previous++;
                    if (value == 0xFFFFFF) terminated++;
                }
                uint first = BinaryPrimitives.ReadUInt32LittleEndian(ram.Slice((int)baseOt, 4));
                uint last = BinaryPrimitives.ReadUInt32LittleEndian(ram.Slice((int)baseOt + 8188, 4));
                Console.WriteLine($"[cm64-world-gate] ORIGINAL_OT_MEMORY first={first:X8} last={last:X8} forward={next} backward={previous} terminators={terminated}");
            }
        }
        CrashWorldSourceProbe.Enter(WorldCall, cpu, memory);
        return true;
    }

    private void After(CpuContext cpu, IMemory memory)
    {
        if (armed) CrashWorldSourceProbe.Leave(WorldCall, true);
    }
}
