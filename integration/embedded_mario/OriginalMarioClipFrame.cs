using System;

namespace RecompOne.Runtime.Host.Window;

public sealed class OriginalMarioClipFrame
{
    internal readonly float[] Vertices;
    public int Tick { get; }
    public int Triangles { get; }

    public OriginalMarioClipFrame(float[] clip, float[] uv, float[] color, int triangles, int tick)
    {
        if (triangles < 1 || triangles > 1024 || tick <= 0 ||
            clip == null || uv == null || color == null ||
            clip.Length != triangles * 12 || uv.Length != triangles * 6 || color.Length != triangles * 9)
            throw new ArgumentException("Expected one coherent bounded homogeneous clip/UV/color frame");
        Tick = tick;
        Triangles = triangles;
        Vertices = new float[triangles * 30];
        for (int triangle = 0; triangle < triangles; triangle++)
        {
            bool textured = false;
            for (int component = triangle * 6; component < triangle * 6 + 6; component++)
                textured |= uv[component] != 1f;
            for (int vertex = triangle * 3; vertex < triangle * 3 + 3; vertex++)
            {
                int offset = vertex * 10;
                for (int component = 0; component < 4; component++)
                    Vertices[offset + component] = Finite(clip[vertex * 4 + component]);
                for (int component = 0; component < 2; component++)
                    Vertices[offset + 4 + component] = Finite(uv[vertex * 2 + component]);
                for (int component = 0; component < 3; component++)
                {
                    float value = Finite(color[vertex * 3 + component]);
                    if (value < 0 || value > 1) throw new ArgumentException("Native color outside normalized range");
                    Vertices[offset + 6 + component] = value;
                }
                Vertices[offset + 9] = textured ? 1 : 0;
            }
        }
    }

    private static float Finite(float value) => float.IsFinite(value)
        ? value : throw new ArgumentException("Non-finite mesh attribute");
}
