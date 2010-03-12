#include "graphserver.h"

//STREET FUNCTIONS
Street*
streetNew(const char *name, double length) {
  Street* ret = (Street*)malloc(sizeof(Street));
  ret->type = PL_STREET;
  ret->name = (char*)malloc((strlen(name)+1)*sizeof(char));
  strcpy(ret->name, name);
  ret->length = length;
  ret->rise = 0;
  ret->fall = 0;
  ret->slog = 1;
  ret->way = 0;
    
  //bind functions to methods
  ret->walk = &streetWalk;
  ret->walkBack = &streetWalkBack;

  return ret;
}

Street*
streetNewElev(const char *name, double length, float rise, float fall) {
    Street* ret = streetNew( name, length );
    ret->rise = rise;
    ret->fall = fall;
    return ret;
}

void
streetDestroy(Street* tokill) {
  free(tokill->name);
  free(tokill);
}

char*
streetGetName(Street* this) {
    return this->name;
}

double
streetGetLength(Street* this) {
    return this->length;
}

float
streetGetRise(Street* this) {
    return this->rise;
}

void
streetSetRise(Street* this, float rise) {
    this->rise = rise;
}

float
streetGetFall(Street* this) {
    return this->fall;
}

void
streetSetFall(Street* this, float fall) {
    this->fall = fall;
}

float
streetGetSlog(Street* this) {
    return this->slog;
}

void
streetSetSlog(Street* this, float slog) {
    this->slog = slog;
}

long
streetGetWay(Street* this) {
    return this->way;   
}

void
streetSetWay(Street* this, long way) {
    this->way = way;
}