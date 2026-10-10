using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using RecompOne.Runtime.Context;
using RecompOne.Runtime.Dispatch;
using RecompOne.Runtime.Memory;
using RecompOne.Runtime.Modding;

public sealed class CrashNativeQueryMod : IMod
{
    private readonly object gate = new();
    private bool armed;
    private long started, epoch;
    private int attempts, receipts, rejects;
    private uint lookupSlot;
    private bool lookupPending;
    private CrashNativeQuery pending;
    public void OnLoad()
    {
        if (Environment.GetEnvironmentVariable("CM64_NATIVE_QUERY_PROBE") != "1") return;
        var candidates = Dispatcher.Overlays.Values.Where(overlay =>
            overlay.Functions.ContainsKey(0x800294B0)).ToArray();
        uint[] required = { 0x800294B0, 0x80015A98, 0x80013B30, 0x80015B58 };
        if (candidates.Length != 1 || required.Any(address => !candidates[0].Functions.ContainsKey(address)))
        {
            Console.WriteLine("[cm64-native-query] BLOCKED missing_or_ambiguous_original_symbols");
            return;
        }
        var functions = candidates[0].Functions;
        HookManager.AddPre(functions[0x800294B0].Method, Begin);
        HookManager.AddPost(functions[0x800294B0].Method, End);
        HookManager.AddPre(functions[0x80015A98].Method, LookupBegin);
        HookManager.AddPost(functions[0x80015A98].Method, LookupEnd);
        HookManager.AddPre(functions[0x80013B30].Method, Reload);
        HookManager.AddPre(functions[0x80015B58].Method, Reload);
        started = Environment.TickCount64; armed = true;
        Console.WriteLine("[cm64-native-query] ARMED receipts_required=true frame_known=false surfaces=false");
    }
    public void OnUnload()
    {
        lock (gate) { armed = false; pending = null; lookupPending = false; ++epoch; }
    }
    private bool Active => armed && Environment.TickCount64 - started <= 90000 &&
        receipts < 24 && rejects < 8;
    private bool Begin(CpuContext context, IMemory memory)
    {
        lock (gate)
        {
            if (!Active || attempts >= 96) { pending = null; return true; }
            try
            {
                if (pending != null) throw new InvalidDataException("NESTED_QUERY");
                if (memory is not PSMemory original || original.Ram.Length != CrashOctree.RamSize)
                    throw new InvalidDataException("RAM_OWNER");
                if (context.A1 != CrashOctree.U32(original.Ram, 0x800566B4)) return true;
                ++attempts;
                pending = new CrashNativeQuery(original.Ram, memory, Environment.CurrentManagedThreadId,
                    ++epoch, context.A0, context.A1, context.A2);
            }
            catch (Exception error) { Reject(error); }
            return true;
        }
    }
    private void End(CpuContext context, IMemory memory)
    {
        lock (gate)
        {
            if (!Active || pending == null) { pending = null; lookupPending = false; return; }
            try
            {
                if (lookupPending || memory is not PSMemory original)
                    throw new InvalidDataException("UNPAIRED_LOOKUP");
                CrashQueryReceipt receipt = pending.Complete(original.Ram, memory,
                    Environment.CurrentManagedThreadId, epoch, context.V0);
                pending = null;
                Console.WriteLine("CM64_NATIVE_QUERY " + JsonSerializer.Serialize(new {
                    version = 1, sequence = ++receipts, phase = "ORIGINAL_QUERY_RETURN",
                    c1Pin = "256fdcef59f15a190290cc19db3fa9a707843b69",
                    launcherPin = "224da7757920a817de2d9242416f657ab95782ea", receipt
                }));
            }
            catch (Exception error) { Reject(error); }
        }
    }
    private bool LookupBegin(CpuContext context, IMemory memory)
    {
        lock (gate)
        {
            if (!Active || pending == null) return true;
            try
            {
                if (lookupPending || memory is not PSMemory original)
                    throw new InvalidDataException("NESTED_LOOKUP");
                pending.LookupStarting(original.Ram, memory, Environment.CurrentManagedThreadId, epoch, context.A0);
                lookupSlot = context.A0; lookupPending = true;
            }
            catch (Exception error) { Reject(error); }
            return true;
        }
    }
    private void LookupEnd(CpuContext context, IMemory memory)
    {
        lock (gate)
        {
            if (!Active || pending == null) return;
            try
            {
                if (!lookupPending || memory is not PSMemory original)
                    throw new InvalidDataException("LOOKUP_PAIR");
                pending.LookupReturned(original.Ram, memory, Environment.CurrentManagedThreadId,
                    epoch, lookupSlot, context.V0);
                lookupPending = false;
            }
            catch (Exception error) { Reject(error); }
        }
    }
    private bool Reload(CpuContext context, IMemory memory)
    {
        lock (gate) { pending = null; lookupPending = false; ++epoch; }
        return true;
    }
    private void Reject(Exception error)
    {
        pending = null; lookupPending = false; ++epoch;
        if (++rejects <= 8) Console.WriteLine("[cm64-native-query] REJECT " + error.GetType().Name + ":" + error.Message);
        if (error is not InvalidDataException) armed = false;
    }
}
