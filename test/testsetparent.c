#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../../core/graph.h"
#include <valgrind/callgrind.h>

int main() {
    Vertex* v1 = vNew("A");
    Vertex* v2 = vNew("B");
    
    Link* origlink = linkNew();
    vLink(v1, v2, (EdgePayload*)origlink);
    vSetParent(v2, v1, (EdgePayload*)linkNew()); //results in invalid write
    
    vDestroy(v1, 1, 1);
    vDestroy(v2, 1, 1);
    linkDestroy(origlink);
    
    return 1;
}
