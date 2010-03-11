#ifndef _EDGETYPES_H_
#define _EDGETYPES_H_

#include <stdlib.h>
#include <string.h>
#include "hashtable_gs.h"
#include "hashtable_itr.h"

#include "graphserver.h"
#include "statetypes.h"

//---------------DECLARATIONS FOR EDGEPAYLOAD CLASS---------------------

struct EdgePayload {
  edgepayload_t type;
  State* (*walk)(struct EdgePayload*, struct State*, struct WalkOptions*);
  State* (*walkBack)(struct EdgePayload*, struct State*, struct WalkOptions*);
} ;

EdgePayload*
epNew( edgepayload_t type, void* payload );

void
epDestroy( EdgePayload* this );

edgepayload_t
epGetType( EdgePayload* this );

State*
epWalk( EdgePayload* this, State* param, WalkOptions* options );

State*
epWalkBack( EdgePayload* this, State* param, WalkOptions* options );

//---------------DECLARATIONS FOR LINK  CLASS---------------------

typedef struct Link {
  edgepayload_t type;
  State* (*walk)(struct EdgePayload*, struct State*, struct WalkOptions*);
  State* (*walkBack)(struct EdgePayload*, struct State*, struct WalkOptions*);
    
  char* name;
} Link;

Link*
linkNew();

void
linkDestroy(Link* tokill);

inline State*
linkWalk(EdgePayload* this, State* param, WalkOptions* options);

inline State*
linkWalkBack(EdgePayload* this, State* param, WalkOptions* options);

char*
linkGetName(Link* this);


//---------------DECLARATIONS FOR HEADWAY  CLASS---------------------

typedef struct Headway {
  edgepayload_t type;
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
} Headway;

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

//---------------DECLARATIONS FOR WAIT CLASS------------------------

typedef struct Wait {
    edgepayload_t type;
    State* (*walk)(struct EdgePayload*, struct State*, struct WalkOptions*);
    State* (*walkBack)(struct EdgePayload*, struct State*, struct WalkOptions*);
    
    long end;
    Timezone* timezone;
} Wait;

Wait*
waitNew(long end, Timezone* timezone);

void
waitDestroy(Wait* tokill);

inline State*
waitWalk(EdgePayload* superthis, State* param, WalkOptions* options);

inline State*
waitWalkBack(EdgePayload* superthis, State* param, WalkOptions* options);

long
waitGetEnd(Wait* this);

Timezone*
waitGetTimezone(Wait* this);

//---------------DECLARATIONS FOR ELAPSE TIME CLASS------------------------

typedef struct ElapseTime {
    edgepayload_t type;
    State* (*walk)(struct EdgePayload*, struct State*, struct WalkOptions*);
    State* (*walkBack)(struct EdgePayload*, struct State*, struct WalkOptions*);
    
    long seconds;
} ElapseTime;

ElapseTime*
elapseTimeNew(long seconds);

void
elapseTimeDestroy(ElapseTime* tokill);

inline State*
elapseTimeWalk(EdgePayload* superthis, State* param, WalkOptions* options);

inline State*
elapseTimeWalkBack(EdgePayload* superthis, State* param, WalkOptions* options);

long
elapseTimeGetSeconds(ElapseTime* this);


//---------------DECLARATIONS FOR STREET  CLASS---------------------

typedef struct Street {
   edgepayload_t type;
   State* (*walk)(struct EdgePayload*, struct State*, struct WalkOptions*);
   State* (*walkBack)(struct EdgePayload*, struct State*, struct WalkOptions*);
    
   char* name;
   double length;
   float rise;
   float fall;
   float slog;
   long way;
} Street;

Street*
streetNew(const char *name, double length);

Street*
streetNewElev(const char *name, double length, float rise, float fall);

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

//---------------DECLARATIONS FOR TRIPBOARD CLASS------------------------------------------

typedef struct TripBoard {
    edgepayload_t type;
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
} TripBoard;

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

//---------------DECLARATIONS FOR EGRESS CLASS---------------------

typedef struct Egress {
   edgepayload_t type;
   State* (*walk)(struct EdgePayload*, struct State*, struct WalkOptions*);
   State* (*walkBack)(struct EdgePayload*, struct State*, struct WalkOptions*);
    
   char* name;
   double length;
} Egress;

Egress*
egressNew(const char *name, double length);

void
egressDestroy(Egress* tokill);

inline State*
egressWalk(EdgePayload* superthis, State* state, WalkOptions* options);

inline State*
egressWalkBack(EdgePayload* superthis, State* state, WalkOptions* options);

char*
egressGetName(Egress* this);

double
egressGetLength(Egress* this);

//---------------DECLARATIONS FOR HEADWAYBOARD CLASS---------------------------------------

typedef struct HeadwayBoard {
    edgepayload_t type;
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
} HeadwayBoard;

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

//---------------DECLARATIONS FOR HEADWAYALIGHT CLASS---------------------------------------

typedef struct HeadwayAlight {
    edgepayload_t type;
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
} HeadwayAlight;

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

//---------------DECLARATIONS FOR CROSSING CLASS-------------------------------------------

typedef struct Crossing {
    edgepayload_t type;
    State* (*walk)(struct EdgePayload*, struct State*, struct WalkOptions*);
    State* (*walkBack)(struct EdgePayload*, struct State*, struct WalkOptions*);
    
    int* crossing_times;
    char** crossing_time_trip_ids;
    int n;
} Crossing;

Crossing*
crNew( );

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

//---------------DECLARATIONS FOR ALIGHT CLASS---------------------------------------------

typedef struct Alight {
    edgepayload_t type;
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
} Alight;

Alight*
alNew( ServiceId service_id, ServiceCalendar* calendar, Timezone* timezone, int agency );

void
alDestroy(Alight* this);

ServiceCalendar*
alGetCalendar( Alight* this );

Timezone*
alGetTimezone( Alight* this );

int
alGetAgency( Alight* this );

ServiceId
alGetServiceId( Alight* this );

int
alGetNumAlightings(Alight* this);

void
alAddAlighting(Alight* this, char* trip_id, int arrival, int stop_sequence);

char*
alGetAlightingTripId(Alight* this, int i);

int
alGetAlightingArrival(Alight* this, int i);

int
alGetAlightingStopSequence(Alight* this, int i);

int
alSearchAlightingsList(Alight* this, int time);

int
alGetLastAlightingIndex(Alight* this, int time);

int
alGetOverage(Alight* this);

int
alGetAlightingIndexByTripId(Alight* this, char* trip_id);

inline State*
alWalk(EdgePayload* this, State* state, WalkOptions* options);

inline State*
alWalkBack(EdgePayload* this, State* state, WalkOptions* options);

typedef struct PayloadMethods {
	void (*destroy)(void*);
	State* (*walk)(void*,State*,WalkOptions*);
	State* (*walkBack)(void*,State*,WalkOptions*);
	//char* (*to_str)(void*);
} PayloadMethods;

typedef struct CustomPayload {
  edgepayload_t type;
  void* soul;
  PayloadMethods* methods;
} CustomPayload;

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
cpWalk(CustomPayload* this, State* state, struct WalkOptions* walkoptions);

State*
cpWalkBack(CustomPayload* this, State* state, struct WalkOptions* walkoptions);

#endif
