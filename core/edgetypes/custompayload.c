#include "../graphserver.h"

// CUSTOM Payload Functions

PayloadMethods*
defineCustomPayloadType(void (*destroy)(void*),
						State* (*walk)(void*,State*,WalkOptions*),
						State* (*walkback)(void*,State*,WalkOptions*)) {
	PayloadMethods* this = (PayloadMethods*)malloc(sizeof(PayloadMethods));
	this->destroy = destroy;
	this->walk = walk;
	this->walkBack = walkback;
	return this;
}

void
undefineCustomPayloadType( PayloadMethods* this ) {
	free(this);
}

CustomPayload*
cpNew( void* soul, PayloadMethods* methods ) {
	CustomPayload* this = (CustomPayload*)malloc(sizeof(CustomPayload));
	this->type = PL_EXTERNVALUE;
	this->soul = soul;
	this->methods = methods;
	return this;
}

void
cpDestroy( CustomPayload* this ) {
	this->methods->destroy(this->soul);
	free( this );
}

void*
cpSoul( CustomPayload* this ) {
	return this->soul;
}

PayloadMethods*
cpMethods( CustomPayload* this ) {
	return this->methods;
}

State*
cpWalk(CustomPayload* this, State* state, WalkOptions* walkoptions) {
	State* s = this->methods->walk(this->soul, state, walkoptions);
	s->prev_edge = (EdgePayload*)this;
	return s;
}
State*
cpWalkBack(CustomPayload* this, State* state, WalkOptions* walkoptions) {
	State* s = this->methods->walkBack(this->soul, state, walkoptions);
	s->prev_edge = (EdgePayload*)this;
	return s;
}
