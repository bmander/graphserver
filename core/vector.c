#include "graphserver.h"

Vector *
vecNew( int init_size, int expand_delta ) {
    Vector *this = (Vector*)malloc(sizeof(Vector));
    
    this->num_elements = 0;
    this->num_alloc = init_size;
    this->expand_delta = expand_delta;
    
    this->elements = (void**)malloc((this->num_alloc)*sizeof(void*));
    
    return this;
}

void
vecDestroy(Vector *this) {
    free(this->elements);
    free(this);
}

void
vecAdd(Vector *this, void *element) {
    if (this->num_elements == this->num_alloc) {
        vecExpand( this, this->expand_delta );
    }
    
    this->elements[this->num_elements] = element;
    this->num_elements += 1;
}

void *
vecGet(Vector *this, int index) {
    if( index < 0 || index >= this->num_elements ) {
        return NULL;
    }
    
    return this->elements[index];
}

void
vecExpand(Vector *this, int amount){
    this->num_alloc += amount;
    this->elements = (void**)realloc( this->elements, this->num_alloc*sizeof(void*) );
}