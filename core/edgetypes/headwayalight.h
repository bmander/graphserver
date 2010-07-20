#ifndef _HEADWAYALIGHT_H_
#define _HEADWAYALIGHT_H_

//---------------DECLARATIONS FOR HEADWAYALIGHT CLASS---------------------------------------

struct HeadwayAlight {
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
};

HeadwayAlight*
haNew(  ServiceId service_id, ServiceCalendar* calendar, Timezone* timezone, int agency, char* trip_id, int start_time, int end_time, int headway_secs );

void
haDestroy(HeadwayAlight* this);

ServiceCalendar*
haGetCalendar( HeadwayAlight* this );

Timezone*
haGetTimezone( HeadwayAlight* this );

int
haGetAgency( HeadwayAlight* this );

ServiceId
haGetServiceId( HeadwayAlight* this );

char*
haGetTripId( HeadwayAlight* this );

int
haGetStartTime( HeadwayAlight* this );

int
haGetEndTime( HeadwayAlight* this );

int
haGetHeadwaySecs( HeadwayAlight* this );

inline State*
haWalk( EdgePayload* superthis, State* state, WalkOptions* options );

inline State*
haWalkBack( EdgePayload* superthis, State* state, WalkOptions* options );

#endif
