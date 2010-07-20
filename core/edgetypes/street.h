#ifndef _STREET_H_
#define _STREET_H_

//---------------DECLARATIONS FOR STREET  CLASS---------------------

struct Street {
   edgepayload_t type;
   long external_id;
   State* (*walk)(struct EdgePayload*, struct State*, struct WalkOptions*);
   State* (*walkBack)(struct EdgePayload*, struct State*, struct WalkOptions*);
    
   char* name;
   double length;
   float rise;
   float fall;
   float slog;
   long way;
    
   int reverse_of_source;
};

Street*
streetNew(const char *name, double length, int reverse_of_source);

Street*
streetNewElev(const char *name, double length, float rise, float fall, int reverse_of_source);

void
streetDestroy(Street* tokill);

inline State*
streetWalk(EdgePayload* superthis, State* state, WalkOptions* options);

inline State*
streetWalkBack(EdgePayload* superthis, State* state, WalkOptions* options);

char*
streetGetName(Street* this);

double
streetGetLength(Street* this);

float
streetGetRise(Street* this);

float
streetGetFall(Street* this);

void
streetSetRise(Street* this, float rise) ;

void
streetSetFall(Street* this, float fall) ;
long
streetGetWay(Street* this);

void
streetSetWay(Street* this, long way);

int
streetGetReverseOfSource(Street* this) ;

#endif
