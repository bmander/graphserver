#ifndef _HEADWAY_H_
#define _HEADWAY_H_

//---------------DECLARATIONS FOR HEADWAY  CLASS---------------------

struct Headway {
  edgepayload_t type;
  long external_id;
  State* (*walk)(struct EdgePayload*, struct State*, struct WalkOptions*);
  State* (*walkBack)(struct EdgePayload*, struct State*, struct WalkOptions*);
    
  int begin_time;
  int end_time;
  int wait_period;
  int transit;
  char* trip_id;
  ServiceCalendar* calendar;
  Timezone* timezone;
  int agency;
  ServiceId service_id;
} ;

Headway*
headwayNew(int begin_time, int end_time, int wait_period, int transit, char* trip_id, ServiceCalendar* calendar, Timezone* timezone, int agency, ServiceId service_id);

void
headwayDestroy(Headway* tokill);

inline State*
headwayWalk(EdgePayload* this, State* param, WalkOptions* options);

inline State*
headwayWalkBack(EdgePayload* this, State* param, WalkOptions* options);

int
headwayBeginTime(Headway* this);

int
headwayEndTime(Headway* this);

int
headwayWaitPeriod(Headway* this);

int
headwayTransit(Headway* this);

char*
headwayTripId(Headway* this);

ServiceCalendar*
headwayCalendar(Headway* this);

Timezone*
headwayTimezone(Headway* this);

int
headwayAgency(Headway* this);

ServiceId
headwayServiceId(Headway* this);

#endif
