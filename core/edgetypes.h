#ifndef _EDGETYPES_H_
#define _EDGETYPES_H_

#include <stdlib.h>
#include <string.h>
#include "hashtable_gs.h"
#include "hashtable_itr.h"
#include "statetypes.h"

typedef struct EdgePayload EdgePayload;

typedef enum {    
  PL_STREET,
  PL_TRIPHOPSCHED_DEPRIC,
  PL_TRIPHOP_DEPRIC,
  PL_LINK,
  PL_EXTERNVALUE,
  PL_NONE, // 5
  PL_WAIT,
  PL_HEADWAY,
  PL_TRIPBOARD,
  PL_CROSSING,
  PL_ALIGHT, // 10
  PL_HEADWAYBOARD,
  PL_EGRESS,
  PL_HEADWAYALIGHT,
  PL_ELAPSE_TIME
} edgepayload_t;

//---------------DECLARATIONS FOR WALKOPTIONS CLASS---------------

typedef struct WalkOptions {
    int transfer_penalty;
    float walking_speed;
    float walking_reluctance;
    float uphill_slowness;
    float downhill_fastness;
    float phase_change_grade;
    float hill_reluctance;    
    int max_walk;
    float walking_overage;
    int turn_penalty;
    
    float phase_change_velocity_factor;
} WalkOptions;

WalkOptions*
woNew();

void
woDestroy( WalkOptions* this );

int
woGetTransferPenalty( WalkOptions* this );

void
woSetTransferPenalty( WalkOptions* this, int transfer_penalty );

float
woGetWalkingSpeed( WalkOptions* this );

void
woSetWalkingSpeed( WalkOptions* this, float walking_speed );

float
woGetWalkingReluctance( WalkOptions* this );

void
woSetWalkingReluctance( WalkOptions* this, float walking_reluctance );

int
woGetMaxWalk( WalkOptions* this );

void
woSetMaxWalk( WalkOptions* this, int max_walk );

float
woGetWalkingOverage( WalkOptions* this );

void
woSetWalkingOverage( WalkOptions* this, float walking_overage );

int
woGetTurnPenalty( WalkOptions* this );

void
woSetTurnPenalty( WalkOptions* this, int turn_penalty );

//---------------DECLARATIONS FOR STATE CLASS---------------------

typedef struct State {
   long          time;           //seconds since the epoch
   long          weight;
   double        dist_walked;    //meters
   int           num_transfers;
   EdgePayload*  prev_edge;
   char*         trip_id;
   int           stop_sequence;
   int           n_agencies;
   ServicePeriod** service_periods;
} State;

State*
stateNew(int numcalendars, long time);

void
stateDestroy( State* this);

State*
stateDup( State* this );

long
stateGetTime( State* this );

long
stateGetWeight( State* this);

double
stateGetDistWalked( State* this );

int
stateGetNumTransfers( State* this );

EdgePayload*
stateGetPrevEdge( State* this );

char*
stateGetTripId( State* this );

int
stateGetStopSequence( State* this );

int
stateGetNumAgencies( State* this );

ServicePeriod*
stateServicePeriod( State* this, int agency );

void
stateSetServicePeriod( State* this,  int agency, ServicePeriod* cal );

void
stateSetTime( State* this, long time );

void
stateSetWeight( State* this, long weight );

void
stateSetDistWalked( State* this, double dist );

void
stateSetNumTransfers( State* this, int n);

// the state does not keep ownership of the trip_id, so the state
// may not live longer than whatever object set its trip_id
void
stateDangerousSetTripId( State* this, char* trip_id );

void
stateSetPrevEdge( State* this, EdgePayload* edge );

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
