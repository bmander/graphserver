#include "hashtable_gs.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include "hashtable.h"
#include "hashtable_utility.h"

static unsigned int
quickhash(void *str)
{
  unsigned long hash = 5381;
  int c;

  while ((c = *(char*)str++))
    hash = ((hash << 5) + hash) + c; /* hash * 33 + c */

  return hash;
}

static int str_eql(void* str1, void* str2) {
  if( strcmp(str1, str2) == 0 )
    return 1;
  else
    return 0;
}

struct hashtable *
create_hashtable_string(unsigned int minsize) {
  struct hashtable *ret = create_hashtable(minsize, quickhash, str_eql);
  return ret;
}

int hashtable_insert_string(struct hashtable *h, const char *key, void *v) {
  size_t length = strlen(key)+1;

  char* permakey = (char*)malloc(length*sizeof(char));
  memcpy( permakey, key, length );

  return hashtable_insert(h, permakey, v);
}

int hashtable_insert_str_long(struct hashtable *h, const char *key, long v) {
  long* permaval = (long*)malloc(sizeof(long));
  *permaval = v;

  return hashtable_insert_string(h, key, permaval); 
}

int hashtable_change_str_long(struct hashtable *h, char *key, long v) {
  long *permaval = (long*)malloc(sizeof(long));
  *permaval = v;

  return hashtable_change(h, key, permaval, 1);
}
