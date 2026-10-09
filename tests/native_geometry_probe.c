/* Isolated synthetic oracle. Includes the PINNED original loader so its private
 * read_surface_data/add_surface remain unchanged. Never linked into either game.
 * Input is preflighted authored geometry, NOT a commercial stream/retail mesh. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
#include <ctype.h>
#include <stdlib.h>
#include "engine/surface_load.c"

s32 gSurfaceNodesAllocated, gSurfacesAllocated, gNumStaticSurfaceNodes, gNumStaticSurfaces;
s16 gCheckingSurfaceCollisionsForCamera, gFindFloorIncludeSurfaceIntangible;
u32 gTimeStopState;
s32 gNumFindFloorMisses;
struct NumTimesCalled gNumCalls;

static struct Surface surfaces[2];
static struct SurfaceNode nodes[256];

/* Fail before calling original unchecked allocators. Limits belong to this
 * isolated fixture, not to a running game's unknown pool capacity. */
static int insert(s16 *vertices, int type, int room, int surface_limit, int node_limit) {
    int count = (upper_cell_index(max_3(vertices[0],vertices[3],vertices[6]))
               - lower_cell_index(min_3(vertices[0],vertices[3],vertices[6]))+1)
              * (upper_cell_index(max_3(vertices[2],vertices[5],vertices[8]))
               - lower_cell_index(min_3(vertices[2],vertices[5],vertices[8]))+1);
    if (gSurfacesAllocated >= surface_limit || gSurfaceNodesAllocated + count > node_limit) return 0;
    s16 indices[] = {0,1,2};
    s16 *index = indices;
    struct Surface *surface = read_surface_data(vertices,&index);
    if (!surface) return 0;
    surface->type = type; surface->room = room;
    add_surface(surface,1);
    return 1;
}

int main(void) {
    char line[512];
    if (!fgets(line,sizeof(line),stdin) || !strchr(line,'\n')) return 2;
    char *cursor=line;
    int input[11];
    for (int i=0;i<11;i++) {
        char *end;
        errno=0;
        long value=strtol(cursor,&end,10);
        if (cursor==end || errno==ERANGE || value<INT_MIN || value>INT_MAX) return 2;
        input[i]=(int)value; cursor=end;
    }
    while (isspace((unsigned char)*cursor)) cursor++;
    if (*cursor) return 2;
    s16 vertices[9];
    for (int i=0;i<9;i++) {
        if (input[i] < -2000 || input[i] > 2000) return 2; /* bounded oracle input */
        vertices[i] = input[i];
    }
    if ((input[9]!=SURFACE_DEFAULT && input[9]!=SURFACE_BURNING) || input[10]<-128 || input[10]>127) return 2;
    sSurfacePool = surfaces; sSurfaceNodePool = nodes; sSurfacePoolSize = 2;
    struct Surface *floor = NULL;
    float x=(vertices[0]+vertices[3]+vertices[6])/3.0f;
    float z=(vertices[2]+vertices[5]+vertices[8])/3.0f;
    assert(find_floor(x,1000,z,&floor)==-11000 && !floor); /* no-insertion control */
    assert(!insert(vertices,input[9],input[10],0,256));
    assert(!insert(vertices,input[9],input[10],2,0));
    assert(gSurfacesAllocated==0 && gSurfaceNodesAllocated==0);
    assert(insert(vertices,input[9],input[10],2,256));
    float height=find_floor(x,1000,z,&floor);
    assert(floor && floor->type==input[9] && floor->room==input[10]);
    assert(floor->normal.y>0.01f);
    printf("height=%.6f ny=%.6f surfaces=%d nodes=%d type=%d room=%d\n",
           height,floor->normal.y,gSurfacesAllocated,gSurfaceNodesAllocated,floor->type,floor->room);
    /* Rejection with a populated partition must not disturb existing contact. */
    int saved_nodes=gSurfaceNodesAllocated;
    assert(!insert(vertices,input[9],input[10],1,256));
    assert(!insert(vertices,input[9],input[10],2,saved_nodes));
    assert(gSurfacesAllocated==1 && gSurfaceNodesAllocated==saved_nodes);
    assert(find_floor(x,1000,z,&floor)==height && floor);
    gTimeStopState=TIME_STOP_ACTIVE;
    clear_dynamic_surfaces();
    assert(find_floor(x,1000,z,&floor)==height && floor);
    gTimeStopState=0;
    clear_dynamic_surfaces();
    assert(gSurfacesAllocated==0 && gSurfaceNodesAllocated==0);
    assert(find_floor(x,1000,z,&floor)==-11000 && !floor);
    puts("VERIFIED_SYNTHETIC: original loader/floor query, bounded fixture pools, control and lifecycle PASS");
    return 0;
}
