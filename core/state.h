#ifndef STATE_H
#define STATE_H

//---------------DECLARATIONS FOR STATE CLASS---------------------

struct State {
   long          time;           //seconds since the epoch
   long          weight;
   double        dist_walked;    //meters
   int           num_transfers;
   EdgePayload*  prev_edge;
   char*         trip_id;
   int           stop_sequence;
   int           n_agencies;
   ServicePeriod** service_periods;
} ;

State*
stateNew(int numcalendars, long time);

void
stateDestroy( State* this);

State*
stateDup( const State* this );

long
stateGetTime( const State* this );

long
stateGetWeight( const State* this);

double
stateGetDistWalked( const State* this );

int
stateGetNumTransfers( const State* this );

EdgePayload*
stateGetPrevEdge( const State* this );

char*
stateGetTripId( const State* this );

int
stateGetStopSequence( const State* this );

int
stateGetNumAgencies( const State* this );

ServicePeriod*
stateServicePeriod( const State* this, int agency );

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

#endif
