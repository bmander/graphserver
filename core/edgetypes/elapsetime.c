//ElapseTime FUNCTIONS
ElapseTime*
elapseTimeNew(long seconds) {
    ElapseTime* ret = (ElapseTime*)malloc(sizeof(ElapseTime));
    ret->type = PL_ELAPSE_TIME;
    ret->seconds = seconds;
    
    ret->walk = elapseTimeWalk;
    ret->walkBack = elapseTimeWalkBack;
    
    return ret;
}

void
elapseTimeDestroy(ElapseTime* tokill) {
    free(tokill);
}

long
elapseTimeGetSeconds(ElapseTime* this) {
    return this->seconds;
}