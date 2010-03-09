
//LINK FUNCTIONS
Link*
linkNew() {
  Link* ret = (Link*)malloc(sizeof(Link));
  ret->type = PL_LINK;
  ret->name = (char*)malloc(5*sizeof(char));
  strcpy(ret->name, "LINK");
    
  //bind functions to methods
  ret->walk = &linkWalk;
  ret->walkBack = &linkWalkBack;

  return ret;
}

void
linkDestroy(Link* tokill) {
  free( tokill->name );
  free( tokill );
}

char*
linkGetName(Link* this) {
    return this->name;
}

int
linkReturnOne(Link* this) {
    return 1;
}
