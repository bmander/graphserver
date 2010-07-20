#ifndef _TRIPBOARD_H_
#define _TRIPBOARD_H_

#define NO_OVERAGE_VALUE -1

//---------------DECLARATIONS FOR TRIPBOARD CLASS------------------------------------------

struct TripBoard {
    edgepayload_t type;
    long external_id;
    State* (*walk)(struct EdgePayload*, struct State*, struct WalkOptions*);
    State* (*walkBack)(struct EdgePayload*, struct State*, struct WalkOptions*);
    
    int n;
    int* departs;
    char** trip_ids;
    int* stop_sequences;
    
    ServiceCalendar* calendar;
    Timezone* timezone;
    int agency;
    ServiceId service_id;
    
    int overage; //number of seconds schedules past midnight of the last departure. If it's at 12:00:00, the overage is 0.
} ;

TripBoard*
tbNew( ServiceId service_id, ServiceCalendar* calendar, Timezone* timezone, int agency );

void
tbDestroy(TripBoard* this);

ServiceCalendar*
tbGetCalendar( TripBoard* this );

Timezone*
tbGetTimezone( TripBoard* this );

int
tbGetAgency( TripBoard* this );

ServiceId
tbGetServiceId( TripBoard* this );

int
tbGetNumBoardings(TripBoard* this);

void
tbAddBoarding(TripBoard* this, char* trip_id, int depart, int stop_sequence);

char*
tbGetBoardingTripId(TripBoard* this, int i);

int
tbGetBoardingDepart(TripBoard* this, int i);

int
tbGetBoardingStopSequence(TripBoard* this, int i);

int
tbSearchBoardingsList(TripBoard* this, int time);

int
tbGetNextBoardingIndex(TripBoard* this, int time);

int
tbGetOverage(TripBoard* this);

inline State*
tbWalk( EdgePayload* superthis, State* state, WalkOptions* options );

inline State*
tbWalkBack( EdgePayload* superthis, State* state, WalkOptions* options );

int
tbGetBoardingIndexByTripId(TripBoard* this, char* trip_id);

#endif
