using RecompOne.Runtime.Host.Window;

internal static partial class Program
{
    private static int checks;
    private static void Check(bool condition, string name)
    {
        if (!condition) throw new InvalidOperationException(name);
        checks++;
    }

    private static void Reject(Action operation, string name)
    {
        try { operation(); }
        catch (ArgumentException) { Check(true, name); return; }
        throw new InvalidOperationException(name);
    }

    private static int Main(string[] args)
    {
        try
        {
            float[] clip = [-1, -1, 0, 1, 1, -1, 0, 2, 0, 1, 0, 4];
            float[] uv = [1, 1, 1, 1, 1, 1];
            float[] rgb = [1, 0, 0, 0, 1, 0, 0, 0, 1];
            var frame = new OriginalMarioClipFrame(clip, uv, rgb, 1, 17);
            Check(frame.Tick == 17 && frame.Triangles == 1, "coherent frame identity");
            Check(frame.Vertices[9] == 0 && frame.Vertices[19] == 0 && frame.Vertices[29] == 0,
                "native all-(1,1) sentinel remains untextured");
            clip[0] = 42; uv[0] = 0; rgb[0] = 0;
            Check(frame.Vertices[0] == -1 && frame.Vertices[4] == 1 && frame.Vertices[6] == 1,
                "snapshot owns all attribute arrays");
            var textured = new OriginalMarioClipFrame(clip, uv, rgb, 1, 18);
            Check(textured.Vertices[9] == 1 && textured.Vertices[19] == 1 && textured.Vertices[29] == 1,
                "texture sentinel is triangle-flat");
            Reject(() => new OriginalMarioClipFrame([], uv, rgb, 1, 1), "reject truncated frame");
            Reject(() => new OriginalMarioClipFrame(clip, uv, rgb, 1025, 1), "reject unbounded frame");
            Reject(() => new OriginalMarioClipFrame(clip, uv, rgb, 1, 0), "reject missing tick");
            clip[0] = float.NaN;
            Reject(() => new OriginalMarioClipFrame(clip, uv, rgb, 1, 1), "reject nonfinite clip");
            clip[0] = 0; uv[0] = float.PositiveInfinity;
            Reject(() => new OriginalMarioClipFrame(clip, uv, rgb, 1, 1), "reject nonfinite UV");
            uv[0] = 0; rgb[0] = 2;
            Reject(() => new OriginalMarioClipFrame(clip, uv, rgb, 1, 1), "reject nonnormalized color");
            Environment.SetEnvironmentVariable("CM64_GPU_SELF_DEPTH", null);
            Check(!OriginalMarioGpu.TryRender(frame, 64, 64, out var disabled) && disabled == 0,
                "default-off seam needs no GL context");
            if (args.Contains("--gpu")) RunGpu();
            Console.WriteLine($"MARIO_GPU_CHECKS_PASS checks={checks} gpu={args.Contains("--gpu")} original_game=NOT_TESTED playable=false");
            return 0;
        }
        catch (Exception error) { Console.Error.WriteLine(error); return 1; }
    }
}
