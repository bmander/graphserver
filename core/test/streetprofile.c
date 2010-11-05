#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../graphserver.h"
#include "../graph.h"
#include <valgrind/callgrind.h>

//This should leak memory
int main() {
    
    Graph* gg = gNew();
    
    //Load up vertices
    FILE* fp = fopen("nodes.csv", "r");
    char vertexid[40];
    while( !feof( fp ) ) {
        fscanf(fp, "%s\n", &vertexid);
        
        gAddVertex(gg, vertexid);
        
        Vertex* vv = gGetVertex(gg, vertexid);
    }
    fclose( fp );
    
    //Load up edges
    fp = fopen("map.csv", "r");
    char via[20];
    char from[20];
    char to[20];
    double length;
    while( !feof( fp ) ){
        fscanf(fp, "%[^,],%[^,],%[^,],%lf\n", &via, &from, &to, &length);
        
        Street* ss = streetNew( via, length, 0 );
        gAddEdge(gg, from, to, (EdgePayload*)ss);
    }
    fclose( fp );

    WalkOptions *wo = woNew();
    
    //Find a shortest-path tree
    
    int i=0;
    for(i=0; i<1; i++) {
        ShortestPathTree* spt;
        spt = gShortestPathTree(gg, "53204010", "bogus", stateNew(1,0), wo, 1000000, 100000, 100000);
        sptDestroy(spt);
        spt = gShortestPathTree(gg, "53116165", "bogus", stateNew(1,0), wo, 10000001, 100000, 100000);
        sptDestroy(spt);
        spt = gShortestPathTree(gg, "53157403", "bogus", stateNew(1,0), wo, 10000001, 100000, 100000);
        sptDestroy(spt);
        spt = gShortestPathTree(gg, "30279744", "bogus", stateNew(1,0), wo, 10000001, 100000, 100000);
        sptDestroy(spt);
        spt = gShortestPathTree(gg, "67539645", "bogus", stateNew(1,0), wo, 10000001, 100000, 100000);
        sptDestroy(spt);
        spt = gShortestPathTree(gg, "53217469", "bogus", stateNew(1,0), wo, 10000001, 100000, 100000);
        sptDestroy(spt);
        spt = gShortestPathTree(gg, "152264675", "bogus", stateNew(1,0), wo, 10000001, 100000, 100000);
        sptDestroy(spt);
        spt = gShortestPathTree(gg, "53062837", "bogus", stateNew(1,0), wo, 10000001, 100000, 100000);
        sptDestroy(spt);
        spt = gShortestPathTree(gg, "53190677", "bogus", stateNew(1,0), wo, 10000001, 100000, 100000);
        sptDestroy(spt);
        spt = gShortestPathTree(gg, "53108368", "bogus", stateNew(1,0), wo, 10000001, 100000, 100000);
        sptDestroy(spt);
        spt = gShortestPathTree(gg, "91264868", "bogus", stateNew(1,0), wo, 10000001, 100000, 100000);
        sptDestroy(spt);
        spt = gShortestPathTree(gg, "53145350", "bogus", stateNew(1,0), wo, 10000001, 100000, 100000);
        sptDestroy(spt);
        spt = gShortestPathTree(gg, "53156103", "bogus", stateNew(1,0), wo, 10000001, 100000, 100000);
        sptDestroy(spt);
        spt = gShortestPathTree(gg, "53139148", "bogus", stateNew(1,0), wo, 10000001, 100000, 100000);
        sptDestroy(spt);
        spt = gShortestPathTree(gg, "108423294", "bogus", stateNew(1,0), wo, 10000001, 100000, 100000);
        sptDestroy(spt);
        spt = gShortestPathTree(gg, "53114499", "bogus", stateNew(1,0), wo, 10000001, 100000, 100000);
        sptDestroy(spt);
        spt = gShortestPathTree(gg, "53110306", "bogus", stateNew(1,0), wo, 10000001, 100000, 100000);
        sptDestroy(spt);
        spt = gShortestPathTree(gg, "53132736", "bogus", stateNew(1,0), wo, 10000001, 100000, 100000);
        sptDestroy(spt);
        spt = gShortestPathTree(gg, "53103049", "bogus", stateNew(1,0), wo, 10000001, 100000, 100000);
        sptDestroy(spt);
        spt = gShortestPathTree(gg, "53178033", "bogus", stateNew(1,0), wo, 10000001, 100000, 100000);
        sptDestroy(spt);
    }
    
    gDestroy(gg);
    woDestroy( wo );
    
    return 1;
} 
