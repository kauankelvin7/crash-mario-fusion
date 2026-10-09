/* Execute unchanged c1 reference queries, NOT the selected Launcher runtime. */
#include <assert.h>
#include <errno.h>
#include <limits.h>
#include "cm64_c1_queries.h" /* Generated exact pinned-source slices, never committed. */
#include "native_fixture_input.h"

_Static_assert(sizeof(zone_query_result)==8,"Reference compact query layout mismatch");
_Static_assert(sizeof(zone_query_result_rect)==16,"Reference descriptor layout mismatch");
_Static_assert(offsetof(zone_rect,octree)==28,"Reference zone layout mismatch");

static int no_event(gool_object *obj, uint32_t node) {
    (void)obj; (void)node;
    abort(); /* Any event path would invalidate the ordinary-fixture hypothesis. */
}

int main(int argc,char **argv) {
    if (argc!=5) return 2;
    int args[4];
    for(int i=0;i<4;i++) {
        char *end; errno=0;
        long value=strtol(argv[i+1],&end,10);
        if(errno || *end || end==argv[i+1] || value<0 || value>128) return 2;
        args[i]=(int)value;
    }
    if(args[0]<1 || args[0]>2) return 2;
    zone_query query={0};
    query.nodes_bound.p2.x=query.nodes_bound.p2.y=query.nodes_bound.p2.z=128*256;
    bound collider={0};
    collider.p1.x=collider.p2.x=args[1]*256;
    collider.p1.y=0; collider.p2.y=args[2]*256;
    collider.p1.z=collider.p2.z=args[3]*256;
    int all_values[12];
    if(!cm64_read_ints(all_values,6*args[0],0,128)) return 2;
    for(int n=0;n<args[0];n++) {
        int *values=&all_values[n*6];
        for(int j=0;j<3;j++) if(values[j+3]==0 || values[j]+values[j+3]>128) return 2;
        zone_rect zone={0};
        zone.x=values[0]; zone.y=values[1]; zone.z=values[2];
        zone.w=values[3]; zone.h=values[4]; zone.d=values[5];
        zone.octree.root=3; /* Explicit authored type-1, no event subtype. */
        int count=ZoneQueryOctree(&zone,&query.nodes_bound,
                  (zone_query_results*)&query.results[query.result_count]);
        assert(count==3);
        zone_query_result *leaf=&query.results[query.result_count+2];
        assert(leaf->level==0 && leaf->node==1);
        assert(leaf->x==zone.x*16 && leaf->y==zone.y*16 && leaf->z==zone.z*16);
        query.result_count+=count;
    }
    zone_query_summary summary={0};
    FindFloorY(NULL,&query,&query.nodes_bound,&collider,args[2]*256,&summary,-1,no_event);
    printf("%d\n",summary.floor_nodes_y);
    return 0;
}
