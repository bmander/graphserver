#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../core/graph.h"
#include <valgrind/callgrind.h>
#include "../core/contraction.h"

#define TRUE 1
#define FALSE 0

int main() {
    
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
        
        Street* s1 = streetNew( via, length );
        gAddEdge(gg, from, to, (EdgePayload*)s1);
        Street* s2 = streetNew( via, length );
        gAddEdge(gg, to, from, (EdgePayload*)s2);
    }
    fclose( fp );
    
    WalkOptions* wo = woNew();
    CH* ch = get_contraction_heirarchies(gg, wo, 1);
    
    gDestroy( ch->up );
    //gDestroyBasic( ch->down, FALSE );
    chDestroy( ch );
    gDestroy( gg );
    woDestroy( wo );
    
    return 1;
} 
