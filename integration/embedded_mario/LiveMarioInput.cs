using System;
using System.Threading;
using CrashMarioFusion.Embedded;

internal sealed record MarioInputSnapshot(long Sequence, long Timestamp, int Epoch,
    bool Active, float StickX, float StickY, bool Jump, long JumpPress = 0);

internal sealed class LiveMarioInput
{
    internal const int MaxTicks = 3600;
    MarioInputSnapshot latest = new(0, 0, 0, false, 0, 0, false);
    long sequence, nextTick, consumedJump;
    int remainder;
    bool released;
    readonly object publishLock = new();
    internal MarioInputSnapshot Latest => Volatile.Read(ref latest);
    internal void Publish(long now, int epoch, bool active, bool left, bool right,
        bool forward, bool backward, bool jump)
    {
        lock (publishLock) PublishOwned(now, epoch, active, left, right, forward, backward, jump);
    }
    void PublishOwned(long now, int epoch, bool active, bool left, bool right,
        bool forward, bool backward, bool jump)
    {
        if (!active || epoch != Latest.Epoch) released = false;
        if (active && !left && !right && !forward && !backward && !jump) released = true;
        float horizontal = (right ? 1 : 0) - (left ? 1 : 0);
        float vertical = (forward ? 1 : 0) - (backward ? 1 : 0);
        if (horizontal != 0 && vertical != 0)
        {
            horizontal *= .70710678f;
            vertical *= .70710678f;
        }
        var previous = Latest;
        long nextSequence = Interlocked.Increment(ref sequence);
        long jumpPress = active && released && jump && !previous.Jump ? nextSequence : previous.JumpPress;
        Volatile.Write(ref latest, new MarioInputSnapshot(nextSequence,
            now, epoch, active && released, horizontal, vertical, jump, jumpPress));
    }
    internal bool TryTick(long now, long frequency, out MarioInputs inputs,
        out MarioInputSnapshot snapshot)
    {
        snapshot = Latest;
        inputs = new MarioInputs { CamLookX = 1, CamLookZ = 0 };
        if (!snapshot.Active || now < snapshot.Timestamp ||
            now - snapshot.Timestamp > frequency / 4)
        {
            nextTick = 0;
            consumedJump = snapshot.JumpPress;
            return false;
        }
        if (nextTick == 0 || now - nextTick > frequency / 4) nextTick = now;
        if (now < nextTick) return false;
        nextTick += frequency / 30;
        remainder += (int)(frequency % 30);
        if (remainder >= 30) { nextTick++; remainder -= 30; }
        inputs.StickX = snapshot.StickX;
        inputs.StickY = snapshot.StickY;
        inputs.ButtonA = (byte)(snapshot.Jump || snapshot.JumpPress > consumedJump ? 1 : 0);
        consumedJump = snapshot.JumpPress;
        return true;
    }
}
