// M4.1B1 original Mario libsm64 colored mesh layered inside Crash's
// actual OutputPanel image rectangle. No calibrated Crash scene camera,
// cross-game z-buffer, textured guest GL FBO, collision or guest memory writes.
using System;
using System.Numerics;
using ImGuiNET;
using RecompOne.Runtime.Host.Window;

internal static class OriginalMarioOutputOverlay
{
    private static bool registered;
    private static int presented;
    private static bool logged;
    private static int firstGuestTick;
    private static int lastGuestTick;

    private readonly struct Tri
    {
        internal readonly Vector2 A, B, C;
        internal readonly float Depth;
        internal readonly uint Color;
        internal Tri(Vector2 a, Vector2 b, Vector2 c, float depth, uint color)
        { A=a; B=b; C=c; Depth=depth; Color=color; }
    }

    public static void Register()
    {
        if (registered) return;
        MenuRegistry.RegisterOutputOverlay(Draw);
        registered = true;
        Console.WriteLine("[cm64-output] ARMED original Mario geometry on Crash image; guest anchoring is UNCALIBRATED");
    }

    public static void Stop()
    {
        if (!registered) return;
        MenuRegistry.UnregisterOutputOverlay(Draw);
        registered = false;
    }

    private static void Draw(Vector2 topLeft, Vector2 bottomRight)
    {
        var frame = OriginalMarioPreview.Current;
        if (frame is null || frame.Triangles == 0) return;
        float width=bottomRight.X-topLeft.X;
        float height=bottomRight.Y-topLeft.Y;
        if (!float.IsFinite(width) || !float.IsFinite(height) ||
            width < 120f || height < 90f || frame.Triangles>1024) return;
        var position=frame.Position;
        var color=frame.Color;
        if (position.Length != frame.Triangles*9 || color.Length != frame.Triangles*9)
            throw new InvalidOperationException("Original guest buffer size mismatch");
        int vertexCount=frame.Triangles*3;
        float minX=float.PositiveInfinity,minY=float.PositiveInfinity,minZ=float.PositiveInfinity;
        float maxX=float.NegativeInfinity,maxY=float.NegativeInfinity,maxZ=float.NegativeInfinity;
        for(int v=0;v<vertexCount;v++)
        {
            int ix=v*3;
            minX=Math.Min(minX,position[ix]);maxX=Math.Max(maxX,position[ix]);
            minY=Math.Min(minY,position[ix+1]);maxY=Math.Max(maxY,position[ix+1]);
            minZ=Math.Min(minZ,position[ix+2]);maxZ=Math.Max(maxZ,position[ix+2]);
        }
        float cx=(minX+maxX)*.5f,cy=(minY+maxY)*.5f,cz=(minZ+maxZ)*.5f;
        float span=Math.Max(1f,Math.Max(maxX-minX,Math.Max(maxY-minY,maxZ-minZ)));
        float scale=Math.Min(width*.23f,height*.32f)/span;
        // A bounded placeholder screen-space anchor, not Crash's original
        // camera coordinates or physical surface mapping.
        Vector2 center=topLeft+new Vector2(width*.52f,height*.67f);
        var list=new Tri[frame.Triangles];
        for(int t=0;t<frame.Triangles;t++)
        {
            var points=new Vector2[3];
            float depth=0,r=0,g=0,b=0;
            for(int v=0;v<3;v++)
            {
                int ix=t*9+v*3;
                float x=position[ix]-cx,y=position[ix+1]-cy,z=position[ix+2]-cz;
                float rx=x*.82f-z*.57f;
                float rz=x*.57f+z*.82f;
                points[v]=center+new Vector2(rx*scale,(-y*.94f+rz*.22f)*scale);
                depth+=rz;
                r+=color[ix];g+=color[ix+1];b+=color[ix+2];
            }
            uint packed=ImGui.ColorConvertFloat4ToU32(new Vector4(
                Math.Clamp(r/3,0f,1f),Math.Clamp(g/3,0f,1f),
                Math.Clamp(b/3,0f,1f),1f));
            list[t]=new Tri(points[0],points[1],points[2],depth/3,packed);
        }
        Array.Sort(list,(a,b)=>b.Depth.CompareTo(a.Depth));
        var draw=ImGui.GetWindowDrawList(); // called within OutputPanel.DrawImage
        draw.PushClipRect(topLeft,bottomRight,true);
        try
        {
            foreach(var tri in list)
                draw.AddTriangleFilled(tri.A,tri.B,tri.C,tri.Color);
        }
        finally {draw.PopClipRect();}
        if(firstGuestTick == 0) firstGuestTick=frame.Tick;
        lastGuestTick=Math.Max(lastGuestTick,frame.Tick);
        if(++presented>=20 && lastGuestTick-firstGuestTick>=30 &&
            lastGuestTick>=120 && !logged)
        {
            logged=true;
            Console.WriteLine("[cm64-output] M41B_OUTPUT_OVERLAY_DREW original_triangles="+
                frame.Triangles+" original_crash_image_bounds=true overlay=true "+
                "guest_tick_first="+firstGuestTick+" guest_tick_last="+lastGuestTick+" "+
                "camera_calibrated=false shared_depth=false shared_collider=false");
        }
    }
}
