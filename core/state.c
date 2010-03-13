
#include "graphserver.h"

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
