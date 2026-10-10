#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include "cm64_native_query.h"

_Static_assert(sizeof(zone_query_result) == 8, "query row");
_Static_assert(sizeof(zone_query_result_rect) == 16, "query descriptor");
_Static_assert(sizeof(zone_query) == 0x1050, "query extent");
_Static_assert(offsetof(zone_query, result_count) == 0x1004, "count offset");
_Static_assert(offsetof(zone_query, nodes_bound) == 0x1008, "bound offset");

entry *cur_zone;
static entry *fixtures[3];
static int lookups;

entry *NSLookup(void *reference) {
    uint32_t identity = *(uint32_t *)reference;
    assert(lookups < 3 && identity == (uint32_t)(101 + lookups * 2));
    return fixtures[lookups++];
}

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    int mode = atoi(argv[1]);
    if (mode < 0 || mode > 2) return 2;
    zone_header header = {0};
    zone_rect rectangles[3] = {0};
    for (int index = 0; index < 3; ++index) {
        fixtures[index] = calloc(1, sizeof(entry) + sizeof(void *) * 3);
        assert(fixtures[index]);
        fixtures[index]->magic = MAGIC_ENTRY;
        fixtures[index]->eid = 101 + index * 2;
        fixtures[index]->type = 7; fixtures[index]->item_count = 2;
        fixtures[index]->items[0] = (uint8_t *)&header;
        fixtures[index]->items[1] = (uint8_t *)&rectangles[index];
        rectangles[index].x = index == 0 ? -32 : index == 2 ? 3000 : 0;
        rectangles[index].y = index == 1 ? 16 : 0;
        rectangles[index].w = rectangles[index].h = rectangles[index].d = 64;
        rectangles[index].octree.root = mode == 1 ? 0 : mode == 2 ? 19 : 3;
        header.neighbors[index] = fixtures[index]->eid;
    }
    header.neighbor_count = 3; cur_zone = fixtures[0];
    zone_query query = {0}; vec position = {0};
    int count = ZoneQueryOctrees(&position, NULL, &query);
    assert(lookups == 3 && query.once == 1 && count == query.result_count);
    assert(count == (mode == 1 ? 4 : 6));
    assert(*(int32_t *)&query.results[count] == -1);
    const uint8_t *bytes = (const uint8_t *)&query;
    for (size_t index = 0; index < sizeof(query); ++index) printf("%02x", bytes[index]);
    putchar('\n');
    for (int index = 0; index < 3; ++index) free(fixtures[index]);
    return 0;
}
