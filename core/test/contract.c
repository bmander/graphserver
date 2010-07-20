#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../graphserver.h"
#include "../graph.h"
#include <valgrind/callgrind.h>
#include "../heap.h"
#include "../contraction.h"
#include <time.h>

#define TRUE 1
#define FALSE 0

void all_the_work() {
    int MAX_IMPORT = 100000000;
    
    Graph* gg = gNew();
    
    //Load up edges
    FILE* fp = fopen("wallingford.csv", "r");
    char via[20];
    char from[20];
    char to[20];
    double length;
    int i=0;
    while( !feof( fp ) && i < MAX_IMPORT){
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
    
    clock_t t0 = clock();
    CH* ch = get_contraction_hierarchies(gg, wo, 1);
    clock_t t1 = clock();
    double time_elapsed = (t1-t0)/(double)CLOCKS_PER_SEC;
    
    printf( "time elapsed (%ld-%ld)/%ld= %lf\n", t1,t0,CLOCKS_PER_SEC,time_elapsed );
    
    //SPT ON SPT_UP
    State *dummy = stateNew(0,0);
    ShortestPathTree* spt = gShortestPathTree( ch->up, "53144830", "bogus", dummy, wo, INFINITY, INFINITY, INFINITY );
    printf( "SPT found: %p\n", spt );
    
    gDestroy( ch->up );
    //gDestroyBasic( ch->down, FALSE );
    chDestroy( ch );
    gDestroy( gg );
    woDestroy( wo );
}

int main() {
    
    all_the_work();
    
    return 1;
} 
