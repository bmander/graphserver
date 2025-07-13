%module vector_swig

%{
#include <stdlib.h>
#include <string.h>

/* Define Vector typedef first */
typedef struct Vector Vector;

/* Define the Vector struct */
struct Vector {
  int num_elements;
  int num_alloc;
  int expand_delta;
  void **elements;
};

/* Include function implementations */
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
        this->num_alloc += this->expand_delta;
        this->elements = (void**)realloc( this->elements, this->num_alloc*sizeof(void*) );
    }
    
    this->elements[this->num_elements] = element;
    this->num_elements += 1;
}

void *
vecGet(const Vector *this, int index) {
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
%}

/* Forward declare Vector typedef for SWIG */
typedef struct Vector Vector;

/* Define the Vector struct for SWIG */
struct Vector {
  int num_elements;
  int num_alloc;
  int expand_delta;
  void **elements;
};

/* Add typemaps to handle Python integers as void pointers */
%typemap(in) void * {
    if (PyLong_Check($input)) {
        $1 = (void*)(PyLong_AsLong($input));
    } else {
        $1 = (void*)$input;
    }
}

%typemap(out) void * {
    $result = PyLong_FromLong((long)$1);
}

/* Declare the functions for SWIG */
Vector *vecNew(int init_size, int expand_delta);
void vecDestroy(Vector *this);
void vecAdd(Vector *this, void *element);
void *vecGet(const Vector *this, int index);
void vecExpand(Vector *this, int amount);

/* Allow Vector objects to be created from Python */
%extend Vector {
    Vector(int init_size = 50, int expand_delta = 50) {
        return vecNew(init_size, expand_delta);
    }
    
    ~Vector() {
        vecDestroy($self);
    }
    
    void add(void *element) {
        vecAdd($self, element);
    }
    
    void *get(int index) {
        return vecGet($self, index);
    }
    
    void expand(int amount) {
        vecExpand($self, amount);
    }
    
    int size() {
        return $self->num_elements;
    }
    
    int capacity() {
        return $self->num_alloc;
    }
    
    int expandDelta() {
        return $self->expand_delta;
    }
}

/* Allow Vector objects to be created from Python */
%extend Vector {
    Vector(int init_size = 50, int expand_delta = 50) {
        return vecNew(init_size, expand_delta);
    }
    
    ~Vector() {
        vecDestroy($self);
    }
    
    void add(void *element) {
        vecAdd($self, element);
    }
    
    void *get(int index) {
        return vecGet($self, index);
    }
    
    void expand(int amount) {
        vecExpand($self, amount);
    }
    
    int size() {
        return $self->num_elements;
    }
    
    int capacity() {
        return $self->num_alloc;
    }
    
    int expandDelta() {
        return $self->expand_delta;
    }
}