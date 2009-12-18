#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../core/graph.h"
#include <valgrind/callgrind.h>
#include "../core/contraction.h"

//This shouldn't leak memory
int main() {
    
    Graph* gg = gNew();
    
    //Load up edges
    FILE* fp = fopen("wallingford.csv", "r");
    char via[20];
    char from[20];
    char to[20];
    double length;
    while( !feof( fp ) ){
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
    
    int n;
    
    long graphsize;
    Vertex** vertices = gVertices( gg, &graphsize);
    int i,j;
    for(i=0; i<graphsize; i++) {
        Path** shortcuts = get_shortcuts( gg, vertices[i], wo, 1, &n );
        printf( "found %d shortcuts for %s (%d/%ld)\n\r", n, vertices[i]->label, i+1, graphsize );
        for(j=0; j<n; j++) {
            pathDestroy( shortcuts[j] );
        }
        free( shortcuts );
    }
    
    free(vertices);
    woDestroy( wo );
    gDestroy(gg);
    
    return 1;
} 
