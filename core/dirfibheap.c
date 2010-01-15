
#include "dirfibheap.h"

dirfibheap_t 
dirfibheap_new(long initSize)
{
  dirfibheap_t ret = (dirfibheap_t)malloc( sizeof(struct dirfibheap) );
  ret->heap = fibheap_new();
  ret->dir = create_hashtable_string(initSize);
  return ret;
}

fibnode_t
dirfibheap_insert_or_dec_key( dirfibheap_t self, State* s, fibheapkey_t priority )
{
  // concatenating vertex label and time gives unique key
  char key[255];
  sprintf(key, "%s__%ld", s->owner->label, s->time);  
  
  fibnode_t fibnode = hashtable_search( self->dir, key );

  if( fibnode ) {
    fibheap_replace_key( self->heap, fibnode, priority );
  } else {
    fibnode = fibheap_insert( self->heap, priority, (void*)s );
    hashtable_insert_string(self->dir, key, fibnode);
  }
  return fibnode;
}

State*
dirfibheap_extract_min( dirfibheap_t self )
{
  State* best = (State*)fibheap_extract_min( self->heap );
  if(best) {
      char key[255];
      sprintf(key, "%s__%ld", best->owner->label, best->time);  
      hashtable_remove(self->dir, key);
  }
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

void
dirfibheap_delete_node( dirfibheap_t self, State* s )
{
    char key[255];
    sprintf(key, "%s__%ld", s->owner->label, s->time);
    // DEBUG 
    // printf("key: %s\n", key);
    fibnode_t fibnode = hashtable_search( self->dir, key );
    if (fibnode) {
        fibheap_delete_node(self->heap, fibnode);
        hashtable_remove(self->dir, key);
    } else {
        // DEBUG 
        // printf("No fibnode found. State is not in queue directory.\n");
    }
}
