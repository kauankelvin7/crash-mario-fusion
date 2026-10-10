/* Bounded original libsm64 Windows ABI probe; authored floor, private owned ROM.
 * Solver state only: does NOT use Crash level geometry, rendering or collision. */
#include "libsm64.h"
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

enum { ROM_BYTES=8388608, VERTICES=SM64_GEO_MAX_TRIANGLES*9, UVS=SM64_GEO_MAX_TRIANGLES*6,
       TEXTURE_BYTES=SM64_TEXTURE_WIDTH*SM64_TEXTURE_HEIGHT*4 };
static uint8_t *read_rom(const char *path) {
    FILE *f=fopen(path,"rb");
    if(!f) return NULL;
    if(fseek(f,0,SEEK_END)||ftell(f)!=ROM_BYTES||fseek(f,0,SEEK_SET)) {fclose(f);return NULL;}
    uint8_t *bytes=malloc(ROM_BYTES);
    if(!bytes) {fclose(f);return NULL;}
    int ok=fread(bytes,1,ROM_BYTES,f)==ROM_BYTES;
    fclose(f);if(!ok) {free(bytes);return NULL;}
    return bytes;
}
int main(int argc,char **argv) {
    if(argc!=2) {fputs("Usage: embedded_probe.exe PRIVATE_OWNED_SM64_ROM\n",stderr);return 2;}
    uint8_t *rom=read_rom(argv[1]);
    if(!rom) {fputs("INVALID_PRIVATE_ROM: 8 MiB original required\n",stderr);return 2;}
    uint8_t *texture=malloc(TEXTURE_BYTES);
    float *position=calloc(VERTICES,sizeof(float));
    float *normal=calloc(VERTICES,sizeof(float));
    float *color=calloc(VERTICES,sizeof(float));
    float *uv=calloc(UVS,sizeof(float));
    int mario=-1,started=0,code=1;
    if(!texture||!position||!normal||!color||!uv) goto cleanup;
    sm64_global_init(rom,texture);started=1;
    struct SM64Surface platform[2]={
      {.type=0,.force=0,.terrain=0,
       .vertices={{-1600,0,-1600},{1600,0,1600},{1600,0,-1600}}},
      {.type=0,.force=0,.terrain=0,
       .vertices={{-1600,0,-1600},{-1600,0,1600},{1600,0,1600}}}
    };
    sm64_static_surfaces_load(platform,2);
    mario=sm64_mario_create(0,250,0);
    if(mario<0) {fputs("NATIVE_MARIO_CREATE_FAILED\n",stderr);goto cleanup;}
    struct SM64MarioInputs input={.camLookX=1.0f,.camLookZ=0};
    struct SM64MarioState state={0};
    struct SM64MarioGeometryBuffers mesh={
        .position=position,.normal=normal,.color=color,.uv=uv,.numTrianglesUsed=0
    };
    unsigned geometry_frames=0,moving_frames=0,airborne_frames=0;
    float x0=0,z0=0,x1=0,z1=0,miny=1e9f,maxy=-1e9f;
    for(int i=0;i<180;i++) {
        input.stickY=i>=70&&i<155?0.75f:0.0f;
        input.buttonA=(uint8_t)(i==125);
        mesh.numTrianglesUsed=0;
        sm64_mario_tick(mario,&input,&state,&mesh);
        if(!isfinite(state.position[0])||!isfinite(state.position[1])||
           !isfinite(state.position[2])||mesh.numTrianglesUsed>SM64_GEO_MAX_TRIANGLES)
          {fputs("INVALID_MARIO_NATIVE_STATE\n",stderr);goto cleanup;}
        if(i==69) {x0=state.position[0];z0=state.position[2];}
        if(i==179) {x1=state.position[0];z1=state.position[2];}
        if(state.position[1]<miny)miny=state.position[1];
        if(state.position[1]>maxy)maxy=state.position[1];
        geometry_frames+=(mesh.numTrianglesUsed>0);
        moving_frames+=(fabsf(state.velocity[0])+fabsf(state.velocity[2])>0.005f);
        airborne_frames+=(i>=125&&state.position[1]>20.0f);
    }
    float travel=hypotf(x1-x0,z1-z0);
    printf("EMBEDDED_LIBSM64_NATIVE frames=180 geometry_frames=%u moving_frames=%u "
           "airborne_frames=%u travel=%.3f minY=%.3f maxY=%.3f "
           "surface=AUTHORED_NOT_CRASH physical_status=BLOCKED\n",
           geometry_frames,moving_frames,airborne_frames,travel,miny,maxy);
    if(geometry_frames<100||moving_frames<20||travel<2.0f||miny< -500.0f)
      {fputs("MARIO_NATIVE_MOVEMENT_NOT_VERIFIED\n",stderr);goto cleanup;}
    code=0;
cleanup:
    if(mario>=0)sm64_mario_delete(mario);
    if(started)sm64_global_terminate();
    free(rom);free(texture);free(position);free(normal);free(color);free(uv);
    return code;
}
