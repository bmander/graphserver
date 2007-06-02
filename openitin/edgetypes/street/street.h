#ifndef _STREET_H_
#define _STREET_H_

#include <stdlib.h>
#include <string.h>

//to be added to the State hash
//   double        dist_walked;    //meters

typedef struct Street {
   char* name;
   double length;
} Street;

Street*
streetNew(const char *name, double length);

void
streetDestroy(Street* tokill);

inline State*
streetWalk(Street* this, State* params);

inline State*
streetWalkBack(Street* this, State* params);

#endif
