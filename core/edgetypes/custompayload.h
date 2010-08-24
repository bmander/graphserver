#ifndef _CUSTOMPAYLOAD_H_
#define _CUSTOMPAYLOAD_H_

struct PayloadMethods {
	void (*destroy)(void*);
	State* (*walk)(void*,State*,WalkOptions*);
	State* (*walkBack)(void*,State*,WalkOptions*);
	//char* (*to_str)(void*);
};

struct CustomPayload {
  edgepayload_t type;
  void* soul;
  PayloadMethods* methods;
};

PayloadMethods*
defineCustomPayloadType(void (*destroy)(void*),
						State* (*walk)(void*,State*,WalkOptions*),
						State* (*walkback)(void*,State*,WalkOptions*));


void
undefineCustomPayloadType( PayloadMethods* this );

CustomPayload*
cpNew( void* soul, PayloadMethods* methods );

void
cpDestroy( CustomPayload* this );

void*
cpSoul( CustomPayload* this );

PayloadMethods*
cpMethods( CustomPayload* this );

State*
cpWalk(CustomPayload* this, State* state, WalkOptions* walkoptions);

State*
cpWalkBack(CustomPayload* this, State* state, WalkOptions* walkoptions);

#endif
