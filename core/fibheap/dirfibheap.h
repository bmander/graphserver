#ifndef DIRFIBHEAP_H
#define DIRFIBHEAP_H

struct dirfibheap {
  struct hashtable *dir;
  struct fibheap *heap;
};

typedef struct dirfibheap* dirfibheap_t;

extern dirfibheap_t dirfibheap_new(long initSize);
extern fibnode_t dirfibheap_insert_or_dec_key ( dirfibheap_t , Vertex* , fibheapkey_t );
extern Vertex* dirfibheap_extract_min ( dirfibheap_t );
extern fibnode_t dirfibheap_get_fibnode( dirfibheap_t self, char* key );
extern int dirfibheap_empty( dirfibheap_t );
extern void dirfibheap_delete ( dirfibheap_t );

#endif
