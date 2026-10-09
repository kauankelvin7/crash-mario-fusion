#ifndef CM64_FIXTURE_INPUT_H
#define CM64_FIXTURE_INPUT_H
#include <errno.h>
#include <limits.h>
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int cm64_read_ints(int *values,int count,int lower,int upper) {
    char line[1024];
    if(count<1 || count>64 || !fgets(line,sizeof(line),stdin) || !strchr(line,'\n')) return 0;
    char *cursor=line;
    for(int i=0;i<count;i++) {
        char *end; errno=0;
        long value=strtol(cursor,&end,10);
        if(errno || end==cursor || value<lower || value>upper) return 0;
        values[i]=(int)value; cursor=end;
    }
    while(isspace((unsigned char)*cursor)) cursor++;
    return *cursor==0;
}
#endif
