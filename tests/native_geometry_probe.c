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

/* MinGW PE/COFF retains references from otherwise-unused original engine
 * sections that ELF --gc-sections discards. Supply fail-fast link stubs ONLY
 * for unrelated full-game entry points. If the exercised floor/loader path
 * ever reaches one, the oracle aborts instead of fabricating a result.
 * This fixture never changes or links these definitions into a game. */
#if defined(_WIN32)
__attribute__((noreturn)) static void unsupported_game_path(void) {
    fputs("ORACLE ERROR: unexpected full-game dependency reached\n", stderr);
    abort();
}
#define FAIL_CLOSED(ret, name, args) ret name args { unsupported_game_path(); }
FAIL_CLOSED(void *, main_pool_alloc, (u32 size, u32 side))
FAIL_CLOSED(void, reset_red_coins_collected, (void))
FAIL_CLOSED(u32, get_special_objects_size, (s16 *data))
FAIL_CLOSED(void, spawn_special_objects, (s16 areaIndex, s16 **specialObjList))
FAIL_CLOSED(void, spawn_macro_objects_hardcoded, (s16 areaIndex, s16 *macroObjList))
FAIL_CLOSED(void, spawn_macro_objects, (s16 areaIndex, s16 *macroObjList))
FAIL_CLOSED(void, obj_build_transform_from_pos_and_angle, (struct Object *obj, s16 posIndex, s16 angleIndex))
FAIL_CLOSED(void, obj_apply_scale_to_matrix, (struct Object *obj, Mat4 dst, Mat4 src))
FAIL_CLOSED(void *, segmented_to_virtual, (const void *addr))
FAIL_CLOSED(f32, dist_between_objects, (struct Object *obj1, struct Object *obj2))
FAIL_CLOSED(void, print_debug_top_down_mapinfo, (const char *str, s32 number))
FAIL_CLOSED(void, set_text_array_x_y, (s32 xOffset, s32 yOffset))
FAIL_CLOSED(void *, vec3s_to_vec3f, (Vec3f dest, Vec3s a))
FAIL_CLOSED(void *, vec3f_dif, (Vec3f dest, Vec3f a, Vec3f b))
FAIL_CLOSED(void *, vec3f_cross, (Vec3f dest, Vec3f a, Vec3f b))
FAIL_CLOSED(f32, vec3f_dot, (Vec3f a, Vec3f b))
FAIL_CLOSED(void *, vec3f_copy, (Vec3f dest, Vec3f src))
FAIL_CLOSED(void *, vec3f_mul, (Vec3f dest, f32 a))
FAIL_CLOSED(void *, vec3f_sum, (Vec3f dest, Vec3f a, Vec3f b))
FAIL_CLOSED(f32, vec3f_length, (Vec3f a))
FAIL_CLOSED(void *, vec3f_normalize, (Vec3f dest))
#undef FAIL_CLOSED
struct Object *gMarioObject;
struct Object *gCurrentObject;
struct MarioState *gMarioState;
const BehaviorScript bhvDddWarp[1] = { 0 };
s16 gCCMEnteredSlide;
s16 *gEnvironmentRegions;
s32 gEnvironmentLevels[20];
#endif

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
