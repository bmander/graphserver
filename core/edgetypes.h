#ifndef _EDGETYPES_H_
#define _EDGETYPES_H_

#include <stdlib.h>
#include <string.h>
#include <statetypes.h>

typedef enum {
  PL_STREET,
  PL_TRIPHOPSCHED,
  PL_LINK,
  PL_RUBYVALUE,
  PL_NONE,
} edgepayload_t;

typedef struct State {
   long          time;           //seconds since the epoch
   long          weight;
   double        dist_walked;    //meters
   int           num_transfers;
   edgepayload_t prev_edge_type;
   char*         prev_edge_name;
   CalendarDay*  calendar_day;
} State;

//STATE
State*
stateNew();

void
stateDestroy();

State*
stateDup( State* this );

//LINK

typedef struct Link {
  char* name;
} Link;

Link*
linkNew();

void
linkDestroy(Link* tokill);

inline State*
linkWalk(Link* this, State* param);

inline State*
linkWalkBack(Link* this, State* param);

//STREET

typedef struct Street {
   char* name;
   double length;
} Street;

Street*
streetNew(const char *name, double length);

void
streetDestroy(Street* tokill);

inline State*
streetWalk(Street* this, State* params);

inline State*
streetWalkBack(Street* this, State* params);

//TRIPHOPSCHEDULE

#define INFINITY 100000000
#define SECONDS_IN_WEEK 604800
#define SECONDS_IN_DAY 86400
#define SECONDS_IN_HOUR 3600
#define SECONDS_IN_MINUTE 60
#define DAYS_IN_WEEK 7

typedef struct TripHop {
  int depart;
  int arrive;
  int transit;
  char* trip_id;
} TripHop;

typedef struct TripHopSchedule {
  int n;
  TripHop* hops;
  ServiceId service_id;
  CalendarDay* calendar;
  double timezone_offset;
} TripHopSchedule;

TripHopSchedule*
thsNew( int *departs, int *arrives, char **trip_ids, int n, ServiceId service_id, CalendarDay* calendar, double timezone_offset );

void
thsDestroy(TripHopSchedule* this);

inline State*
thsWalk(TripHopSchedule* this, State* params);

inline State*
thsWalkBack(TripHopSchedule* this, State* params);

inline TripHop* 
thsGetNextHop(TripHopSchedule* this, long time);

inline TripHop*
thsGetLastHop(TripHopSchedule* this, long time);

#endif
