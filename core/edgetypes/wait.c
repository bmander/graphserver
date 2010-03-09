
//WAIT FUNCTIONS
Wait*
waitNew(long end, Timezone* timezone) {
    Wait* ret = (Wait*)malloc(sizeof(Wait));
    ret->type = PL_WAIT;
    ret->end = end;
    ret->timezone = timezone;
    
    ret->walk = waitWalk;
    ret->walkBack = waitWalkBack;
    
    return ret;
}

void
waitDestroy(Wait* tokill) {
    free(tokill);
}

long
waitGetEnd(Wait* this) {
    return this->end;
}

Timezone*
waitGetTimezone(Wait* this) {
    return this->timezone;
}