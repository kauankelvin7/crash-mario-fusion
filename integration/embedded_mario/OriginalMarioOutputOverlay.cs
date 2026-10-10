// M4.1B2A host-textured original libsm64 Mario triangles inside Crash image.
// Original GPU atlas owned by the privately patched Crash render host, not VSync.
// Screen-space anchor/occlusion/physical Crash collider remain UNCALIBRATED.
using System;
using System.Numerics;
using ImGuiNET;
using RecompOne.Runtime.Host.Window;

internal static class OriginalMarioOutputOverlay
{
    private static bool registered, logged, textureLogged;
    private static int presented, firstGuestTick, lastGuestTick;
    private readonly struct Tri
    {
        internal readonly Vector2 A,B,C,UvA,UvB,UvC;
        internal readonly uint ColorA,ColorB,ColorC;
        internal readonly float Depth;
        internal readonly bool WithoutTexture;
        internal Tri(Vector2 a,Vector2 b,Vector2 c,Vector2 ua,Vector2 ub,
            Vector2 uc,uint ca,uint cb,uint cc,float depth,bool untextured)
        {
            A=a;B=b;C=c;UvA=ua;UvB=ub;UvC=uc;
            ColorA=ca;ColorB=cb;ColorC=cc;Depth=depth;
            WithoutTexture=untextured;
        }
    }
    public static void Register()
    {
        if(registered)return;
        MenuRegistry.RegisterOutputOverlay(Draw);
        registered=true;
        Console.WriteLine("[cm64-output] ARMED original Mario native mesh on Crash image; coordinates UNCALIBRATED");
    }
    public static void Stop()
    {
        if(!registered)return;
        MenuRegistry.UnregisterOutputOverlay(Draw);
        registered=false;
    }
    private static void Draw(Vector2 topLeft,Vector2 bottomRight)
    {
        var frame=OriginalMarioPreview.Current;
        if(frame is null||frame.Triangles==0)return;
        float w=bottomRight.X-topLeft.X,h=bottomRight.Y-topLeft.Y;
        if(!float.IsFinite(w)||!float.IsFinite(h)||w<120||h<90||frame.Triangles>1024)return;
        var pos=frame.Position;var rgb=frame.Color;var uv=frame.Uv;
        if(pos.Length!=frame.Triangles*9||rgb.Length!=frame.Triangles*9||
           uv.Length!=frame.Triangles*6)throw new InvalidOperationException("Original guest mesh/UV sizes invalid");
        int vertices=frame.Triangles*3;
        float minX=float.PositiveInfinity,minY=float.PositiveInfinity,minZ=float.PositiveInfinity;
        float maxX=float.NegativeInfinity,maxY=float.NegativeInfinity,maxZ=float.NegativeInfinity;
        for(int i=0;i<vertices;i++)
        {
            int k=i*3;
            minX=Math.Min(minX,pos[k]);maxX=Math.Max(maxX,pos[k]);
            minY=Math.Min(minY,pos[k+1]);maxY=Math.Max(maxY,pos[k+1]);
            minZ=Math.Min(minZ,pos[k+2]);maxZ=Math.Max(maxZ,pos[k+2]);
        }
        float cx=(minX+maxX)*.5f,cy=(minY+maxY)*.5f,cz=(minZ+maxZ)*.5f;
        float span=Math.Max(1f,Math.Max(maxX-minX,Math.Max(maxY-minY,maxZ-minZ)));
        float scale=Math.Min(w*.23f,h*.32f)/span;
        Vector2 center=topLeft+new Vector2(w*.52f,h*.67f); // authored diagnostic anchor
        var triangles=new Tri[frame.Triangles];
        for(int t=0;t<frame.Triangles;t++)
        {
            var points=new Vector2[3];var coords=new Vector2[3];var colors=new uint[3];
            bool untextured=true;float depth=0;
            for(int v=0;v<3;v++)
            {
                int k=t*9+v*3,j=t*6+v*2;
                float x=pos[k]-cx,y=pos[k+1]-cy,z=pos[k+2]-cz;
                float rx=x*.82f-z*.57f,rz=x*.57f+z*.82f;
                points[v]=center+new Vector2(rx*scale,(-y*.94f+rz*.22f)*scale);
                depth+=rz;
                coords[v]=new Vector2(uv[j],uv[j+1]);
                if(uv[j]!=1f||uv[j+1]!=1f)untextured=false;
                colors[v]=ImGui.ColorConvertFloat4ToU32(new Vector4(
                    Math.Clamp(rgb[k],0,1),Math.Clamp(rgb[k+1],0,1),
                    Math.Clamp(rgb[k+2],0,1),1));
            }
            triangles[t]=new Tri(points[0],points[1],points[2],coords[0],coords[1],
                coords[2],colors[0],colors[1],colors[2],depth/3,untextured);
        }
        Array.Sort(triangles,(a,b)=>b.Depth.CompareTo(a.Depth));
        var draw=ImGui.GetWindowDrawList();
        nint atlas=OriginalMarioAtlas.TextureId;
        int texturedTriangles=0,coloredTriangles=0;
        draw.PushClipRect(topLeft,bottomRight,true);
        try
        {
            foreach(var tri in triangles)
            {
                if(atlas==0||tri.WithoutTexture)
                {
                    // libsm64 marks untextured faces with (1,1). Preserve them
                    // as colored, rather than sampling transparent atlas padding.
                    draw.AddTriangleFilled(tri.A,tri.B,tri.C,tri.ColorA);
                    coloredTriangles++;
                    continue;
                }
                draw.PushTextureID(atlas);
                try
                {
                    // Original libsm64 UVs and per-vertex colors (not stock art).
                    draw.PrimReserve(3,3);
                    draw.PrimVtx(tri.A,tri.UvA,tri.ColorA);
                    draw.PrimVtx(tri.B,tri.UvB,tri.ColorB);
                    draw.PrimVtx(tri.C,tri.UvC,tri.ColorC);
                }
                finally { draw.PopTextureID(); }
                texturedTriangles++;
            }
        }
        finally{draw.PopClipRect();}
        if(firstGuestTick==0)firstGuestTick=frame.Tick;
        lastGuestTick=Math.Max(lastGuestTick,frame.Tick);
        if(atlas!=0 && texturedTriangles>0 && !textureLogged &&
           lastGuestTick-firstGuestTick>=30 && lastGuestTick>=120)
        {
            textureLogged=true;
            Console.WriteLine("[cm64-atlas] M41B2_TEXTURED_MESH_DREW original_textured_triangles="+
                texturedTriangles+" native_guest_tick="+frame.Tick+" authored_screen_anchor=true "+
                "shared_camera=false shared_depth=false shared_collider=false");
        }
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
