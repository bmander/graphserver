#ifndef _ALIGHT_H_
#define _ALIGHT_H_

//---------------DECLARATIONS FOR ALIGHT CLASS---------------------------------------------

struct TripAlight {
    edgepayload_t type;
    long external_id;
    State* (*walk)(struct EdgePayload*, struct State*, struct WalkOptions*);
    State* (*walkBack)(struct EdgePayload*, struct State*, struct WalkOptions*);
    
    int n;
    int* arrivals;
    char** trip_ids;
    int* stop_sequences;
    
    ServiceCalendar* calendar;
    Timezone* timezone;
    int agency;
    ServiceId service_id;
    
    int overage; //number of seconds schedules past midnight of the last departure. If it's at 12:00:00, the overage is 0.
} ;

TripAlight*
alNew( ServiceId service_id, ServiceCalendar* calendar, Timezone* timezone, int agency );

void
alDestroy(TripAlight* this);

ServiceCalendar*
alGetCalendar( TripAlight* this );

Timezone*
alGetTimezone( TripAlight* this );

int
alGetAgency( TripAlight* this );

ServiceId
alGetServiceId( TripAlight* this );

int
alGetNumAlightings(TripAlight* this);

void
alAddAlighting(TripAlight* this, char* trip_id, int arrival, int stop_sequence);

char*
alGetAlightingTripId(TripAlight* this, int i);

int
alGetAlightingArrival(TripAlight* this, int i);

int
alGetAlightingStopSequence(TripAlight* this, int i);

int
alSearchAlightingsList(TripAlight* this, int time);

int
alGetLastAlightingIndex(TripAlight* this, int time);

int
alGetOverage(TripAlight* this);

int
alGetAlightingIndexByTripId(TripAlight* this, char* trip_id);

inline State*
alWalk(EdgePayload* this, State* state, WalkOptions* options);

inline State*
alWalkBack(EdgePayload* this, State* state, WalkOptions* options);

#endif
