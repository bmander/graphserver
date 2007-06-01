#ifndef HASHTABLE_GS_H
#define HASHTABLE_GS_H

#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include "hashtable.h"
#include "hashtable_utility.h"

struct hashtable *
create_hashtable_string(unsigned int minsize);

int hashtable_insert_string(struct hashtable *h, const char *key, void *v);

int hashtable_insert_str_long(struct hashtable *h, const char *key, long v);

int hashtable_change_str_long(struct hashtable *h, char *key, long v);

#endif
