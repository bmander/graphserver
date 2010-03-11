#include "edgetypes.h"
#include "edgetypes/link.h"
#include "edgetypes/street.h"
#include "edgetypes/egress.h"
#include "edgetypes/wait.h"
#include "edgetypes/elapsetime.h"
#include "edgetypes/headway.h"
#include "edgetypes/tripboard.h"
#include "edgetypes/headwayboard.h"
#include "edgetypes/headwayalight.h"
#include "edgetypes/crossing.h"
#include "edgetypes/alight.h"
#include "edgetypes/custom.h"
#include "math.h"
#include <stdio.h>

//---------------DEFINITIONS FOR WALKOPTIONS CLASS---------------

WalkOptions*
woNew() {
    WalkOptions* ret = (WalkOptions*)malloc( sizeof(WalkOptions) );
    ret->transfer_penalty = 0;
    ret->turn_penalty = 0;
    ret->walking_speed = 6.07; //meters per second
    ret->walking_reluctance = 1;
    ret->uphill_slowness = 0.05; //Factor by which someone's speed is slowed going uphill.
    ret->downhill_fastness = -12.1; // meters per second per grade percentage
    ret->phase_change_grade = 0.045; // Grade. An interesting thing happens at a particular grade, when they settle in for a long slog.
    ret->hill_reluctance = 0; //Factor by which an uphill stretch is penalized, in addition to whatever time is lost by simply gaining.
    ret->max_walk = 10000; //meters
    ret->walking_overage = 0.1;
    
    // velocity between 0 grade and the phase change grade is Ax^2+Bx+C, where A is the phase_change_velocity_factor, B is the downhill fastness, and C is the average speed
    float phase_change_speed = (ret->uphill_slowness*ret->walking_speed)/(ret->uphill_slowness+ret->phase_change_grade);
    ret->phase_change_velocity_factor = (phase_change_speed - ret->downhill_fastness*ret->phase_change_grade - ret->walking_speed)/(ret->phase_change_grade*ret->phase_change_grade);
        
    return ret;
}

void
woDestroy( WalkOptions* this ) {
    free(this);
}

int
woGetTransferPenalty( WalkOptions* this ) {
    return this->transfer_penalty;
}

void
woSetTransferPenalty( WalkOptions* this, int transfer_penalty ) {
    this->transfer_penalty = transfer_penalty;
}

float
woGetWalkingSpeed( WalkOptions* this ) {
    return this->walking_speed;
}

void
woSetWalkingSpeed( WalkOptions* this, float walking_speed ) {
    this->walking_speed = walking_speed;
}

float
woGetWalkingReluctance( WalkOptions* this ) {
    return this->walking_reluctance;
}

void
woSetWalkingReluctance( WalkOptions* this, float walking_reluctance ) {
    this->walking_reluctance = walking_reluctance;
}

float
woGetUphillSlowness( WalkOptions* this ) {
    return this->uphill_slowness;
}

void
woSetUphillSlowness( WalkOptions* this, float uphill_slowness ) {
    this->uphill_slowness = uphill_slowness;
}

float
woGetDownhillFastness( WalkOptions* this ) {
    return this->downhill_fastness;
}

void
woSetDownhillFastness( WalkOptions* this, float downhill_fastness ) {
    this->downhill_fastness = downhill_fastness;
}

float
woGetHillReluctance( WalkOptions* this ) {
    return this->hill_reluctance;
}

void
woSetHillReluctance( WalkOptions* this, float hill_reluctance ) {
    this->hill_reluctance = hill_reluctance;
}

int
woGetMaxWalk( WalkOptions* this ) {
    return this->max_walk;
}

void
woSetMaxWalk( WalkOptions* this, int max_walk ) {
    this->max_walk = max_walk;
}

float
woGetWalkingOverage( WalkOptions* this ) {
    return this->walking_overage;
}

void
woSetWalkingOverage( WalkOptions* this, float walking_overage ) {
    this->walking_overage = walking_overage;
}

int
woGetTurnPenalty( WalkOptions* this ) {
    return this->turn_penalty;
}

void
woSetTurnPenalty( WalkOptions* this, int turn_penalty ) {
    this->turn_penalty = turn_penalty;
}

//STATE FUNCTIONS
State*
stateNew(int n_agencies, long time) {
  State* ret = (State*)malloc( sizeof(State) );
  ret->time = time;
  ret->weight = 0;
  ret->dist_walked = 0;
  ret->num_transfers = 0;
  ret->trip_id = NULL;
  ret->stop_sequence = -1;
  ret->prev_edge = NULL;
  ret->n_agencies = n_agencies;
  ret->service_periods = (ServicePeriod**)malloc(n_agencies*sizeof(ServicePeriod*)); //hash of strings->calendardays

  int i;
  for(i=0; i<n_agencies; i++) {
      ret->service_periods[i] = NULL;
  }

  return ret;
}

State*
stateDup( State* this ) {
  State* ret = (State*)malloc( sizeof(State) );
  memcpy( ret, this, sizeof( State ) );

  ret->service_periods = (ServicePeriod**)malloc(this->n_agencies*sizeof(ServicePeriod*)); //hash of strings->calendardays
  memcpy( ret->service_periods, this->service_periods, this->n_agencies*sizeof(ServicePeriod*));

  return ret;
}

//the State object does not own State#calendar
void
stateDestroy(State* this) {
  free( this->service_periods );
  free( this );
}

long
stateGetTime( State* this ) { return this->time; }

long
stateGetWeight( State* this) { return this->weight; }

double
stateGetDistWalked( State* this ) { return this->dist_walked; }

int
stateGetNumTransfers( State* this ) { return this->num_transfers; }

EdgePayload*
stateGetPrevEdge( State* this ) { return this->prev_edge; }

char*
stateGetTripId( State* this ) { return this->trip_id; }

int
stateGetStopSequence( State* this ) { return this->stop_sequence; }

int
stateGetNumAgencies( State* this ) { return this->n_agencies; }

ServicePeriod*
stateServicePeriod( State* this, int agency ) { return this->service_periods[agency]; }

void
stateSetTime( State* this, long time ) { this->time = time; }

void
stateSetWeight( State* this, long weight ) { this->weight = weight; }

void
stateSetDistWalked( State* this, double dist ) { this->dist_walked = dist; }

void
stateSetNumTransfers( State* this, int n) { this->num_transfers = n; }

void
stateSetServicePeriod( State* this,  int agency, ServicePeriod* cal ) { this->service_periods[agency] = cal; }

// the state does not keep ownership of the trip_id, so the state
// may not live longer than whatever object set its trip_id
void
stateDangerousSetTripId( State* this, char* trip_id ) { this->trip_id = trip_id; }

void
stateSetPrevEdge( State* this, EdgePayload* edge ) { this->prev_edge = edge; }

//--------------------EDGEPAYLOAD FUNCTIONS-------------------

EdgePayload*
epNew( edgepayload_t type, void* payload ) {
  EdgePayload* ret = (EdgePayload*)malloc(sizeof(EdgePayload));
  ret->type = PL_NONE;
  return ret;
}

EdgePayload*
epDup( EdgePayload* this ) {
  EdgePayload* ret = (EdgePayload*)malloc( sizeof(EdgePayload) );
  memcpy( ret, this, sizeof( EdgePayload ) );
  return ret;
}

void
epDestroy( EdgePayload* this ) {
  switch( this->type ) {
    case PL_STREET:
      streetDestroy( (Street*)this );
      break;
    case PL_LINK:
      linkDestroy( (Link*)this );
      break;
    case PL_EXTERNVALUE:
      cpDestroy( (CustomPayload*)this );
      break;
    case PL_WAIT:
      waitDestroy( (Wait*)this );
      break;
    case PL_HEADWAY:
      headwayDestroy( (Headway*)this );
      break;
    case PL_EGRESS:
      egressDestroy( (Egress*)this ); 
      break;
    default:
      free( this );
  }
}

edgepayload_t
epGetType( EdgePayload* this ) {
    return this->type;
}

State*
epWalk( EdgePayload* this, State* state, WalkOptions* options ) {
  if( !this )
    return NULL;

  if( this->type == PL_EXTERNVALUE ) {
    return cpWalk( (CustomPayload*)this, state, options );
  }
  
  return this->walk( this, state, options );

}

State*
epWalkBack( EdgePayload* this, State* state, WalkOptions* options ) {
  if(!this)
    return NULL;

  if( this->type == PL_EXTERNVALUE ){
    return cpWalkBack( (CustomPayload*)this, state, options );
  }
  
  return this->walkBack( this, state, options );
}

#undef ROUTE_REVERSE
#include "edgeweights.c"
#define ROUTE_REVERSE
#include "edgeweights.c"
#undef ROUTE_REVERSE
