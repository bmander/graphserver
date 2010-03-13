
#include "../graphserver.h"
#include "fibheap.h"
#include "../graph.h"
#include "dirfibheap.h"
#include <stdlib.h>
#include "../hashtable/hashtable_gs.h"
#include "../hashtable/hashtable.h"

dirfibheap_t 
dirfibheap_new(long initSize)
{
  dirfibheap_t ret = (dirfibheap_t)malloc( sizeof(struct dirfibheap) );
  ret->heap = fibheap_new();
  ret->dir = create_hashtable_string(initSize);
  return ret;
}

fibnode_t
dirfibheap_insert_or_dec_key( dirfibheap_t self, Vertex* vtx, fibheapkey_t priority )
{
  char* key = vtx->label;
  
  fibnode_t fibnode = hashtable_search( self->dir, key );

  if( fibnode ) {
    fibheap_replace_key( self->heap, fibnode, priority );
  } else {
    fibnode = fibheap_insert( self->heap, priority, (void*)vtx );
    hashtable_insert_string(self->dir, key, fibnode);

  }
  return fibnode;
}

Vertex*
dirfibheap_extract_min( dirfibheap_t self )
{
  Vertex* best = (Vertex*)fibheap_extract_min( self->heap );
  if(best) 
    hashtable_remove(self->dir, best->label);
  return best;
}

fibnode_t
dirfibheap_get_fibnode( dirfibheap_t self, char* key ) {
  return hashtable_search( self->dir, key );
}

int
dirfibheap_empty( dirfibheap_t self ) {
  return fibheap_empty( self->heap );
}

void
dirfibheap_delete( dirfibheap_t self )
{
  hashtable_destroy( self->dir, 0 ); //do not delete values in queue
  fibheap_delete( self->heap );
  free( self );
}
