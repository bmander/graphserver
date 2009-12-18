#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../core/graph.h"
#include <valgrind/callgrind.h>

int main() {
    
    Street *s1 = streetNew( "A", 1, 0 );
    Street *s2 = streetNew( "B", 2, 0 );
    Combination* c1 = comboNew( 2 );
    comboAdd( c1, (EdgePayload*)s1 );
    comboAdd( c1, (EdgePayload*)s2 );
    
    Street *s3 = streetNew( "C", 3, 0 );
    Combination *c2 = comboNew( 2 );
    comboAdd( c2, (EdgePayload*)c1 );
    comboAdd( c2, (EdgePayload*)s3 );
    
    State* state1 = stateNew( 0, 0 );
    WalkOptions* wo = woNew();
    State *state2 = epWalk( (EdgePayload*)c2, state1, wo );
    
    streetDestroy( s1 );
    streetDestroy( s2 );
    streetDestroy( s3 );
    comboDestroy( c1 );
    comboDestroy( c2 );
    stateDestroy( state1 );
    stateDestroy( state2 );
    woDestroy( wo );
    
    return 1;
} 
