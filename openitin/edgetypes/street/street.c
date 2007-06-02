#include "edgetypes.h"
#include "math.h"
#include <stdio.h>


//STREET FUNCTIONS
Street*
streetNew(const char *name, double length) {
  Street* ret = (Street*)malloc(sizeof(Street));
  ret->name = (char*)malloc((strlen(name)+1)*sizeof(char));
  strcpy(ret->name, name);
  ret->length = length;

  return ret;
}

void
streetDestroy(Street* tokill) {
  free(tokill->name);
  free(tokill);
}

#undef ROUTE_REVERSE
#include "streetweight.c"
#define ROUTE_REVERSE
#include "streetweight.c"
#undef ROUTE_REVERSE
