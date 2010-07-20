#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../graphserver.h"
#include "../graph.h"
#include "../heap.h"
#include <valgrind/callgrind.h>
#include "../contraction.h"
#include "../fibheap/fibheap.h"

int main() {
    
    int MAX_IMPORT = 100;
    
    Graph* gg = gNew();

    //Load up edges
    FILE* fp = fopen("map.csv", "r");
    char via[20];
    char from[20];
    char to[20];
    double length;
    int i=0;
    while( !feof( fp ) && i < MAX_IMPORT ){
        i++;
        
        fscanf(fp, "%[^,],%[^,],%[^,],%lf\n", &via, &from, &to, &length);
        
        gAddVertex( gg, from );
        gAddVertex( gg, to );
        
        Street* s1 = streetNew( via, length, 0 );
        gAddEdge(gg, from, to, (EdgePayload*)s1);
        Street* s2 = streetNew( via, length, 0 );
        gAddEdge(gg, to, from, (EdgePayload*)s2);
    }
    fclose( fp );
    
    WalkOptions* wo = woNew();
    Heap* pq = init_priority_queue( gg, wo, 1 );
    
    while( !heapEmpty(pq) ) {
        long prio;
        Vertex* next = pqPop( pq, &prio );
        printf( "next vertex: %p has prio: %d\n", next, prio );
    }
    
    heapDestroy( pq );
    woDestroy( wo );
    gDestroy(gg);
    
    return 1;
} 
