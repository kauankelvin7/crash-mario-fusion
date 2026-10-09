/* Asset-free M0 API probe. Synthetic geometry; no Mario/game initialization. */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include "libsm64.h"

static void expect_floor(float expected) {
    float actual = sm64_surface_find_floor_height(0, 200, 0);
    assert(isfinite(actual) && fabsf(actual - expected) < 0.01f);
}

int main(void) {
    struct SM64Surface triangle = {
        .vertices = {{-100, 0, -100}, {0, 0, 100}, {100, 0, -100}}
    };
    sm64_static_surfaces_load(&triangle, 1);
    expect_floor(0);
    /* Pinned libsm64 surface_collision.h expands SM64's lower bound to -110000. */
    assert(sm64_surface_find_floor_height(5000, 200, 5000) == -110000);

    struct SM64SurfaceObject platform = {
        .transform = {.position = {0, 50, 0}},
        .surfaceCount = 1, .surfaces = &triangle
    };
    uint32_t id = sm64_surface_object_create(&platform);
    expect_floor(50);
    platform.transform.position[1] = 80;
    sm64_surface_object_move(id, &platform.transform);
    expect_floor(80);
    sm64_surface_object_delete(id);
    expect_floor(0);

    triangle.vertices[0][1] = 25;
    triangle.vertices[1][1] = 25;
    triangle.vertices[2][1] = 25;
    sm64_static_surfaces_load(&triangle, 1);
    expect_floor(25);
    sm64_static_surfaces_load(NULL, 0);
    expect_floor(-110000);
    puts("VERIFIED_SYNTHETIC: 7 floor/platform/lifecycle checks passed; no game tick.");
    return 0;
}
