#ifndef HASHTABLE_GS_H
#define HASHTABLE_GS_H

struct hashtable *
create_hashtable_string(unsigned int minsize);

int hashtable_insert_string(struct hashtable *h, const char *key, uint32_t v);

#endif
