#ifndef _HEADWAYBOARD_H_
#define _HEADWAYBOARD_H_

//---------------DECLARATIONS FOR HEADWAYBOARD CLASS---------------------------------------

struct HeadwayBoard {
    edgepayload_t type;
    long external_id;
    State* (*walk)(struct EdgePayload*, struct State*, struct WalkOptions*);
    State* (*walkBack)(struct EdgePayload*, struct State*, struct WalkOptions*);
    
    ServiceId service_id;
    char* trip_id;
    int start_time;
    int end_time;
    int headway_secs;
    
    ServiceCalendar* calendar;
    Timezone* timezone;
    int agency;
} ;

HeadwayBoard*
hbNew(  ServiceId service_id, ServiceCalendar* calendar, Timezone* timezone, int agency, char* trip_id, int start_time, int end_time, int headway_secs );

void
hbDestroy(HeadwayBoard* this);

ServiceCalendar*
hbGetCalendar( HeadwayBoard* this );

Timezone*
hbGetTimezone( HeadwayBoard* this );

int
hbGetAgency( HeadwayBoard* this );

ServiceId
hbGetServiceId( HeadwayBoard* this );

char*
hbGetTripId( HeadwayBoard* this );

int
hbGetStartTime( HeadwayBoard* this );

int
hbGetEndTime( HeadwayBoard* this );

int
hbGetHeadwaySecs( HeadwayBoard* this );

inline State*
hbWalk( EdgePayload* superthis, State* state, WalkOptions* options );

inline State*
hbWalkBack( EdgePayload* superthis, State* state, WalkOptions* options );

#endif
