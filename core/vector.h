struct Vector {
  int num_elements;
  int num_alloc;
  int expand_delta;
    
  void **elements;
} ;

// VECTOR FUNCTIONS

Vector *
vecNew( int init_size, int expand_delta );

void
vecDestroy(Vector *this);

void
vecAdd(Vector *this, void *element);

void *
vecGet(Vector *this, int index);

void
vecExpand(Vector *this, int amount);