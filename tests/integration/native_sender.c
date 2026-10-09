/* Synthetic driver for the exact production C sender, not a game runtime. */
#include "cm64_coin.h"
#include <stdio.h>
int main(void) {
    int command;
    while ((command=getchar())!=EOF) {
        if (command=='c') cm64_coin(42,7,1.25f,2.5f,-3.75f);
    }
    return 0;
}
