#ifndef _CROSSING_H_
#define _CROSSING_H_

//---------------DECLARATIONS FOR CROSSING CLASS-------------------------------------------

struct Crossing {
    edgepayload_t type;
    long external_id;
    State* (*walk)(struct EdgePayload*, struct State*, struct WalkOptions*);
    State* (*walkBack)(struct EdgePayload*, struct State*, struct WalkOptions*);
    
    int* crossing_times;
    char** crossing_time_trip_ids;
    int n;
} ;

Crossing*
crNew(void);

void
crDestroy(Crossing* this);

void
crAddCrossingTime(Crossing* this, char* trip_id, int crossing_time);

int
crGetCrossingTime(Crossing* this, char* trip_id);

char*
crGetCrossingTimeTripIdByIndex(Crossing* this, int i);

int
crGetCrossingTimeByIndex(Crossing* this, int i);

int
crGetSize(Crossing* this);

inline State*
crWalk( EdgePayload* superthis, State* state, WalkOptions* options );

inline State*
crWalkBack( EdgePayload* superthis, State* state, WalkOptions* options );

#endif
