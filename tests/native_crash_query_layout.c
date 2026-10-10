#include <stddef.h>
#include "solid.h"
_Static_assert(sizeof(void *) == 4, "guest pointer width");
_Static_assert(sizeof(zone_world) == 64, "guest world width");
_Static_assert(offsetof(zone_header, neighbor_count) == 0x210, "guest neighbor count");
_Static_assert(offsetof(zone_header, neighbors) == 0x214, "guest neighbor slots");
_Static_assert(offsetof(entry, items) == 16, "guest item table");
_Static_assert(offsetof(zone_rect, octree) == 28, "guest rectangle");
_Static_assert(sizeof(zone_query) == 0x1050, "guest query extent");
_Static_assert(offsetof(zone_query, result_count) == 0x1004, "guest query count");
_Static_assert(offsetof(zone_query, nodes_bound) == 0x1008, "guest query bounds");
