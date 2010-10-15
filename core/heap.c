//#include <stdlib.h>
//#include <string.h>
//#include "heap.h"
#include "graphserver.h"

Heap* heapNew( int init_capacity ) {
    Heap* this = (Heap*)malloc(sizeof(Heap));
    this->nodes = (HeapNode*)malloc( (init_capacity+1)*sizeof(HeapNode) );
    this->capacity = init_capacity;
    this->size = 0;
    return this;
}

void heapDestroy( Heap* this ) {
    free( this->nodes );
    free( this );
}

void heapDouble( Heap *this ) {
    this->capacity = this->capacity * 2;
    this->nodes = (HeapNode*)realloc( this->nodes, (this->capacity+1)*sizeof(HeapNode) );
}

void heapInsert( Heap* this, void* payload, long priority ) {
    if( this->size == this->capacity ) {
        heapDouble( this );
    }
    
    this->size++;
    int hole = this->size;
    
    this->nodes[ 0 ].payload = payload;
    this->nodes[ 0 ].priority = priority;
    
    // so long as the inserted priority is lower than the current priority, keep moving up the tree
    while( priority < this->nodes[ hole / 2 ].priority ) {
        this->nodes[ hole ] = this->nodes[ hole / 2 ];
        hole /= 2;
    }
    
    this->nodes[ hole ].payload = payload;
    this->nodes[ hole ].priority = priority;
}

int heapEmpty( Heap* this ) {
    return this->size == 0;
}

void* heapMin( Heap* this, long* priority ) {
    if( this->size == 0 ) {
        return NULL;
    } else {
        *priority = this->nodes[1].priority;
        return this->nodes[1].payload;
    }
}

void heapPercolateDown( Heap* this, int hole ) {
    int child;
    HeapNode tmp = this->nodes[ hole ];
    
    while( hole * 2 <= this->size ) {
        
        child = hole * 2;
        if( child != this->size && this->nodes[ child + 1 ].priority < this->nodes[ child ].priority ) {
            child++;
        }
              
        if( this->nodes[ child ].priority < tmp.priority ) {
            this->nodes[ hole ] = this->nodes[ child ];
        } else {
            break;
        }
        
        hole = child;
    }
    
    this->nodes[ hole ] = tmp;
}

void* heapPop( Heap* this, long* priority ) {
    void* ret = heapMin( this, priority );
    
    this->nodes[1] = this->nodes[ this->size ];
    this->size--;
    heapPercolateDown( this, 1 );
    
    return ret;
}
