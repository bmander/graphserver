#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../core/graph.h"
#include <valgrind/callgrind.h>

int main() {
    SPTVertex* vv = sptvNew( "home" );
    sptvDestroy( vv, 1, 1 );
    
    return 1;
}
