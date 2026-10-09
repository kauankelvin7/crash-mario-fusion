/* Reuse authored test pools/native loader glue; discard its triangle-test main. */
#define main cm64_unused_triangle_main
#include "native_geometry_probe.c"
#undef main
#include "native_fixture_input.h"

int main(int argc,char **argv) {
    if(argc!=5) return 2;
    int args[4];
    for(int i=0;i<4;i++) {
        char *end; errno=0;
        long value=strtol(argv[i+1],&end,10);
        if(errno || *end || end==argv[i+1] || value<0 || value>128) return 2;
        args[i]=(int)value;
    }
    if(args[0]!=2 && args[0]!=4) return 2;
    static struct Surface box_surfaces[4];
    sSurfacePool=box_surfaces; sSurfacePoolSize=4; sSurfaceNodePool=nodes;
    int values[36];
    if(!cm64_read_ints(values,9*args[0],0,128)) return 2;
    for(int n=0;n<args[0];n++) {
        s16 vertices[9];
        for(int j=0;j<9;j++) {
            vertices[j]=values[n*9+j];
        }
        if(!insert(vertices,SURFACE_DEFAULT,0,4,256)) return 2;
    }
    struct Surface *floor=NULL;
    f32 height=find_floor(args[1],args[2],args[3],&floor);
    printf("%.6f\n",floor ? height : -1.0f);
    clear_dynamic_surfaces();
    assert(gSurfacesAllocated==0 && gSurfaceNodesAllocated==0);
    assert(find_floor(args[1],args[2],args[3],&floor)==-11000 && !floor);
    return 0;
}
