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
    int transfer_slack;
    int max_transfers;
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

int
woGetTransferSlack( WalkOptions* this );

void
woSetTransferSlack( WalkOptions* this, int turn_penalty );

int
woGetMaxTransfers( WalkOptions* this );

void
woSetMaxTransfers( WalkOptions* this, int turn_penalty );

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
   struct State*   next;
   struct Vertex*  owner;
   struct Edge*    back_edge;
   struct State*   back_state;
   struct fibnode* queue_node;
   int             initial_wait;
} State;

State*
stateNew(int numcalendars, long time);

void
stateDestroy( State* this);

State*
stateDup( State* this );

State*
stateNext( State* this );

struct Vertex*
stateOwner( State* this );

struct Edge*
stateBackEdge( State* this );

State*
stateBackState( State* this );

int
stateInitialWait( State* this);

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

#endif
