#ifndef CM64_POSE_H
#define CM64_POSE_H
#include <stdint.h>
/* Observer lifecycle only; never mutates native game state. */
void cm64_pose_invalidate(void);
void cm64_pose(uint32_t tick, int16_t level, int16_t area,
               const float pos[3], const int16_t angles[3], uint32_t action, uint32_t flags);
#endif
