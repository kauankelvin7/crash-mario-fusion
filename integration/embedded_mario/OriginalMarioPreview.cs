// M4.1 diagnostic: draw the actual original libsm64 CPU mesh through the
// Crash host's existing OpenGL/ImGui render path, in a SEPARATE preview.
// No GL calls on Pad/VSync, no fake shared camera, occlusion or Crash collision.
using System;
using System.Numerics;
using System.Threading;
using ImGuiNET;
using RecompOne.Runtime.Host.Window;

internal sealed class OriginalMarioMeshFrame
{
    public readonly float[] Position;
    public readonly float[] Color;
    public readonly int Triangles;
    public readonly int Tick;
    public OriginalMarioMeshFrame(float[] position, float[] color, int triangles, int tick)
        => (Position, Color, Triangles, Tick) = (position, color, triangles, tick);
}

internal static unsafe class OriginalMarioPreview
{
    private static OriginalMarioMeshFrame? current;
    internal static OriginalMarioMeshFrame? Current => Volatile.Read(ref current);
    private static bool windowOpen = true;
    private static bool registered;
    private static bool renderLogged;
    private static int framesDrawn;

    // Called only by the already-bounded native Mario solver callback.
    // A complete immutable snapshot prevents render/physics pointer races.
    public static void Publish(float* positions, float* colors, ushort triangleCount, int tick)
    {
        if (positions == null || colors == null || triangleCount > 1024 || tick <= 0)
            throw new InvalidOperationException("Invalid guest CPU mesh snapshot");
        int components = checked(triangleCount * 9);
        float[] vertex = new float[components], rgb = new float[components];
        for (int i = 0; i < components; ++i)
        {
            float p = positions[i], c = colors[i];
            if (!float.IsFinite(p) || !float.IsFinite(c))
                throw new InvalidOperationException("Guest mesh contains non-finite data");
            vertex[i] = p;
            rgb[i] = Math.Clamp(c, 0f, 1f);
        }
        Volatile.Write(ref current, new OriginalMarioMeshFrame(vertex, rgb, triangleCount, tick));
    }

    public static void Register()
    {
        if (registered) return;
        registered = true;
        MenuRegistry.RegisterWindow(Draw);
    }

    public static void Stop()
    {
        Volatile.Write(ref current, null);
        windowOpen = false;
    }

    private readonly struct Projected
    {
        public readonly Vector2 A, B, C;
        public readonly float Depth;
        public readonly uint Color;
        public Projected(Vector2 a, Vector2 b, Vector2 c, float depth, uint color)
            => (A, B, C, Depth, Color) = (a, b, c, depth, color);
    }

    private static void Draw()
    {
        if (!windowOpen) return;
        var data = Volatile.Read(ref current);
        if (data == null || data.Triangles == 0) return;
        ImGui.SetNextWindowSize(new Vector2(460, 500), ImGuiCond.FirstUseEver);
        ImGui.SetNextWindowPos(new Vector2(56, 72), ImGuiCond.FirstUseEver);
        if (!ImGui.Begin("Mario native geometry | M4.1 diagnostic", ref windowOpen))
        {
            ImGui.End();
            return;
        }
        try
        {
            ImGui.TextUnformatted("Original libsm64 triangles, authored floor");
            ImGui.TextUnformatted("NOT composited with Crash camera or depth");
            ImGui.Text($"Native tick {data.Tick}   triangles {data.Triangles}");
            Vector2 available = ImGui.GetContentRegionAvail();
            float side = Math.Clamp(Math.Min(available.X, available.Y) - 6f, 80f, 410f);
            var corner = ImGui.GetCursorScreenPos();
            var size = new Vector2(side, side);
            var draw = ImGui.GetWindowDrawList();
            var bg = ImGui.ColorConvertFloat4ToU32(new Vector4(.095f, .11f, .14f, 1f));
            draw.AddRectFilled(corner, corner + size, bg);
            draw.PushClipRect(corner, corner + size, true);
            try
            {
                int vertices = data.Triangles * 3;
                float minX=float.PositiveInfinity,minY=float.PositiveInfinity,minZ=float.PositiveInfinity;
                float maxX=float.NegativeInfinity,maxY=float.NegativeInfinity,maxZ=float.NegativeInfinity;
                for(int i=0;i<vertices;++i)
                {
                    int n=i*3; var p=data.Position;
                    minX=Math.Min(minX,p[n]); maxX=Math.Max(maxX,p[n]);
                    minY=Math.Min(minY,p[n+1]); maxY=Math.Max(maxY,p[n+1]);
                    minZ=Math.Min(minZ,p[n+2]); maxZ=Math.Max(maxZ,p[n+2]);
                }
                float cx=(minX+maxX)*.5f,cy=(minY+maxY)*.5f,cz=(minZ+maxZ)*.5f;
                float radius=Math.Max(1f,Math.Max(maxX-minX,Math.Max(maxY-minY,maxZ-minZ)));
                float scale=side*.65f/radius;
                var tris = new Projected[data.Triangles];
                for(int t=0;t<data.Triangles;t++)
                {
                    var points = new Vector2[3];
                    float depth=0, rr=0,gg=0,bb=0;
                    for(int v=0;v<3;v++)
                    {
                        int idx=t*9+v*3;
                        float x=data.Position[idx]-cx;
                        float y=data.Position[idx+1]-cy;
                        float z=data.Position[idx+2]-cz;
                        float rx=x*.82f-z*.57f;
                        float rz=x*.57f+z*.82f;
                        points[v]=corner+new Vector2(side*.5f+rx*scale,side*.53f+(-y*.94f+rz*.22f)*scale);
                        depth+=rz;
                        rr+=data.Color[idx];gg+=data.Color[idx+1];bb+=data.Color[idx+2];
                    }
                    uint color=ImGui.ColorConvertFloat4ToU32(new Vector4(
                        Math.Clamp(rr/3,0f,1f),Math.Clamp(gg/3,0f,1f),Math.Clamp(bb/3,0f,1f),1f));
                    tris[t]=new Projected(points[0],points[1],points[2],depth/3,color);
                }
                Array.Sort(tris,(a,b)=>b.Depth.CompareTo(a.Depth));
                foreach(var triangle in tris)
                    draw.AddTriangleFilled(triangle.A,triangle.B,triangle.C,triangle.Color);
                ++framesDrawn;
                if (!renderLogged && framesDrawn>=5)
                {
                    renderLogged=true;
                    Console.WriteLine("[cm64-embedded] M41_PREVIEW_DREW native_mesh=true original_triangles="+data.Triangles+
                        " guest_window=true shared_scene=false shared_depth=false");
                }
            }
            finally { draw.PopClipRect(); }
            ImGui.Dummy(size);
        }
        catch (Exception ex)
        {
            // Disable only the preview; never interrupt original Crash rendering.
            windowOpen = false;
            Console.Error.WriteLine("[cm64-embedded] M41_PREVIEW_DISABLED " + ex.GetType().Name);
        }
        finally { ImGui.End(); }
    }
}
