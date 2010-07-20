#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../graphserver.h"
#include "../graph.h"
#include <valgrind/callgrind.h>
#include "../heap.h"

#define TRUE 1
#define FALSE 0

int main() {
    
    Heap* hh = heapNew( 1 );
    
    heapInsert( hh, "first", 1 );
    
    long pp;
    char* itemout = heapPop( hh, &pp );
    
    printf( "%s\n", itemout );
    printf( "size:%d\n", hh->size );
    
    heapInsert( hh, "one", 1 );
    heapInsert( hh, "ten", 10 );

    while( !heapEmpty( hh ) ) {
        itemout = heapPop( hh, &pp );
        printf( "%s\n", itemout );
        printf( "size:%d\n", hh->size );
    }
    
    heapInsert( hh, "ten", 10 );
    heapInsert( hh, "one", 1 );

    while( !heapEmpty( hh ) ) {
        itemout = heapPop( hh, &pp );
        printf( "%s\n", itemout );
        printf( "size:%d\n", hh->size );
    }
    
    heapInsert( hh, "384", 384 );
    heapInsert( hh, "887", 887 );
    heapInsert( hh, "778", 778 );

    while( !heapEmpty( hh ) ) {
        itemout = heapPop( hh, &pp );
        printf( "%s\n", itemout );
        printf( "size:%d\n", hh->size );
    }
    
    int i;
    for(i=0; i<1000; i++) {
        char* payload = (char*)malloc(200*sizeof(char));
        long priority = rand()%1000+1;
        sprintf(payload, "%ld", priority);
        
        printf( "inserting '%s' with priority %ld\n", payload, priority );
        
        heapInsert( hh, payload, priority );
    }
    
    while( !heapEmpty( hh ) ) {
        itemout = heapPop( hh, &pp );
        printf( "%s\n", itemout );
        printf( "size:%d\n", hh->size );
        free(itemout);
    }
    
    heapDestroy( hh );
    
    return 1;
} 
