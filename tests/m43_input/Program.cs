using System;
using System.Threading.Tasks;

static class Program
{
    static int count;
    static void Check(bool condition)
    {
        if (!condition) throw new Exception("Input contract assertion " + (count + 1));
        count++;
    }
    static void Main()
    {
        var input = new LiveMarioInput();
        Check(!input.TryTick(100, 3000, out _, out _));
        input.Publish(100, 1, true, false, true, true, false, true);
        Check(!input.TryTick(100, 3000, out _, out _));
        input.Publish(100, 1, true, false, false, false, false, false);
        Check(input.TryTick(100, 3000, out var native, out var snapshot));
        Check(native.ButtonA == 0 && snapshot.Sequence == 2);
        input.Publish(200, 1, true, false, true, true, false, true);
        Check(input.TryTick(200, 3000, out native, out snapshot));
        Check(Math.Abs(native.StickX * native.StickX + native.StickY * native.StickY - 1) < .00001 && native.ButtonA == 1);
        Check(!input.TryTick(201, 3000, out _, out _));
        Check(!input.TryTick(951, 3000, out _, out _));
        input.Publish(1000, 2, true, false, true, false, false, true);
        Check(!input.Latest.Active);
        input.Publish(1000, 2, false, false, false, false, false, false);
        input.Publish(1100, 2, true, false, true, false, false, true);
        Check(!input.Latest.Active);
        input.Publish(1100, 2, true, false, false, false, false, false);
        Check(input.TryTick(1100, 3000, out _, out _));
        input.Publish(1200, 2, true, true, true, true, true, false);
        Check(input.TryTick(1200, 3000, out native, out _) && native.StickX == 0 && native.StickY == 0);
        var clock = new LiveMarioInput();
        int ticks = 0;
        for (long time = 1; time < 3001; time++)
        {
            clock.Publish(time, 1, true, false, false, false, false, false);
            if (clock.TryTick(time, 3000, out _, out _)) ticks++;
        }
        Check(ticks == 30);
        var concurrent = new LiveMarioInput();
        var writer = Task.Run(() => { for (int index = 1; index <= 10000; index++) concurrent.Publish(index, 1, true, false, false, false, false, false); });
        long sequence = 0;
        while (!writer.IsCompleted)
        {
            var current = concurrent.Latest;
            if (current.Sequence < sequence) throw new Exception("Torn snapshot");
            sequence = current.Sequence;
        }
        writer.GetAwaiter().GetResult();
        Check(concurrent.Latest.Sequence == 10000);
        var quick = new LiveMarioInput();
        quick.Publish(100, 1, true, false, false, false, false, false);
        Check(quick.TryTick(100, 3000, out _, out _));
        quick.Publish(110, 1, true, false, false, false, false, true);
        quick.Publish(120, 1, true, false, false, false, false, false);
        Check(quick.TryTick(200, 3000, out native, out _) && native.ButtonA == 1);
        quick.Publish(300, 1, true, false, false, false, false, false);
        Check(quick.TryTick(300, 3000, out native, out _) && native.ButtonA == 0);
        Console.WriteLine("M43_INPUT_CONTRACT assertions=" + count + " VERIFIED_SYNTHETIC native_game=NOT_TESTED");
    }
}
