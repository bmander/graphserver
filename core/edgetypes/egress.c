//EGRESS FUNCTIONS
Egress*
egressNew(const char *name, double length) {
  Egress* ret = (Egress*)malloc(sizeof(Egress));
  ret->type = PL_EGRESS;
  ret->name = (char*)malloc((strlen(name)+1)*sizeof(char));
  strcpy(ret->name, name);
  ret->length = length;
  
  //bind functions to methods
  ret->walk = &egressWalk;
  ret->walkBack = &egressWalkBack;

  return ret;
}

void
egressDestroy(Egress* tokill) {
  free(tokill->name);
  free(tokill);
}

char*
egressGetName(Egress* this) {
    return this->name;
}

double
egressGetLength(Egress* this) {
    return this->length;
}