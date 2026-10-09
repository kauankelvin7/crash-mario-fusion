/* Deterministic driver for the production observer, not a game runtime. */
#include "cm64_pose.h"
#include <stdio.h>
#include <math.h>
#include <inttypes.h>
uint64_t cm64_pose_test_ms;
int main(void) {
    uint32_t tick;
    int level, area;
    char mode;
    while (scanf("%" SCNu64 " %" SCNu32 " %d %d %c", &cm64_pose_test_ms,
                 &tick, &level, &area, &mode)==5) {
        float pos[3]={1.25f,2.5f,-3.75f};
        int16_t angles[3]={-32768,0,32767};
        if (mode=='i') { cm64_pose_invalidate(); continue; }
        if (mode=='n') pos[1]=NAN;
        cm64_pose(tick,(int16_t)level,(int16_t)area,pos,angles,0x12345678,0x80000001);
    }
    return 0;
}
