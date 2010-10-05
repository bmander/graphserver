#ifndef _HEAP_H_
#define _HEAP_H_

struct HeapNode {
    long priority;
    void *payload;
} ;

struct Heap {
    struct HeapNode* nodes;
    int capacity;
    int size;
} ;

Heap* heapNew( int init_capacity ) ;

void heapDestroy( Heap* this ) ;

void heapInsert( Heap* this, void* payload, long priority ) ;

int heapEmpty( Heap* this ) ;

void* heapMin( Heap* this, long* priority ) ;

void* heapPop( Heap* this, long* priority ) ;

#endif
