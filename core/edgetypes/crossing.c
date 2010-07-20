#include "../graphserver.h"

// CROSSING FUNCTIONS

Crossing*
crNew( ) {
  Crossing* ret = (Crossing*)malloc(sizeof(Crossing));
  ret->external_id = 0;
  ret->type = PL_CROSSING;
  ret->n = 0;
  ret->crossing_times = NULL;
  ret->crossing_time_trip_ids = NULL;
    
  ret->walk = &crWalk;
  ret->walkBack = &crWalkBack;
    
  return ret;
}

void
crDestroy(Crossing* this) {
    int i;
    for(i=0; i<this->n; i++) {
        free(this->crossing_time_trip_ids[i]);
    }
    free(this->crossing_time_trip_ids);
    free(this->crossing_times);
    free(this);
}

void
crAddCrossingTime(Crossing* this, char* trip_id, int crossing_time) {
    // init the trip_id, depart list
    if(this->n==0) {
        this->crossing_times = (int*)malloc(sizeof(int));
        this->crossing_time_trip_ids = (char**)malloc(sizeof(char*));
        
        this->crossing_times[0] = crossing_time;
        
        int n = strlen(trip_id)+1;
        this->crossing_time_trip_ids[0] = (char*)malloc(sizeof(char)*(n));
        memcpy(this->crossing_time_trip_ids[0], trip_id, n);
        
    } else {
        //allocate new, expanded lists with size enough for the extra departure
        int* next_crossing_times = (int*)malloc((this->n+1)*sizeof(int));
        char** next_crossing_time_trip_ids = (char**)malloc((this->n+1)*sizeof(char*));
        
        //copy old list to new list up to insertion point
        int i;
        for(i=0; i<this->n; i++) {
            next_crossing_times[i] = this->crossing_times[i];
            next_crossing_time_trip_ids[i] = this->crossing_time_trip_ids[i];
        }
        
        //copy new departure into lists
        next_crossing_times[this->n] = crossing_time;
        int strn = strlen(trip_id)+1;
        next_crossing_time_trip_ids[this->n] = (char*)malloc(sizeof(char)*(strn));
        memcpy(next_crossing_time_trip_ids[this->n], trip_id, strn);
        
        //free and replace old lists
        free(this->crossing_times);
        free(this->crossing_time_trip_ids);
        this->crossing_times = next_crossing_times;
        this->crossing_time_trip_ids = next_crossing_time_trip_ids;
    }
    
    this->n += 1;
}

int
crGetCrossingTime(Crossing* this, char* trip_id) {
    int i;
    for(i=0; i<this->n; i++) {
        if( strcmp(this->crossing_time_trip_ids[i], trip_id)==0 ) {
            return this->crossing_times[i];
        }
    }
    return -1;
}

char*
crGetCrossingTimeTripIdByIndex(Crossing* this, int i) {
    if(i<0 || i>=this->n) {
        return NULL;
    }
    return this->crossing_time_trip_ids[i];
}
    

int
crGetCrossingTimeByIndex(Crossing* this, int i) {
    if(i<0 || i>=this->n) {
        return -1;
    }
    return this->crossing_times[i];
}

int
crGetSize(Crossing* this) {
    return this->n;
}

inline State*
crWalk( EdgePayload* superthis, State* state, WalkOptions* options ) {
    Crossing* this = (Crossing*)superthis;
    
    // the state must have a trip_id, or else we don't know how long they'll spend on the bus
    if( state->trip_id==NULL ) {
        return NULL;
    }
    
    // get the crossing time as a function of the trip
    int crossing_time = crGetCrossingTime( this, state->trip_id );
    
    // bail if you're on a trip that doesn't cross this crossing
    if(crossing_time==-1) {
        return NULL;
    }
    
    // Dupe state and advance time by the waiting time
    State* ret = stateDup( state );
    
    ret->time   += crossing_time;
    ret->weight += crossing_time;
    
    // Make sure the service period caches are updated if we've traveled over a service period boundary
    int i;
    for(i=0; i<state->n_agencies; i++) {
        if( ret->service_periods[i] && ret->time >= ret->service_periods[i]->end_time) {
          ret->service_periods[i] = ret->service_periods[i]->next_period;
        }
    }
    
    return ret;
    
}

inline State*
crWalkBack( EdgePayload* superthis, State* state, WalkOptions* options ) {
    Crossing* this = (Crossing*)superthis;
    
    // the state must have a trip_id, or else we don't know how long they'll spend on the bus
    if( state->trip_id==NULL ) {
        return NULL;
    }
    
    // get the crossing time as a function of the trip
    int crossing_time = crGetCrossingTime( this, state->trip_id );
    
    // bail if you're on a trip that doesn't cross this crossing
    if(crossing_time==-1) {
        return NULL;
    }
    
    // Dupe state and advance time by the waiting time
    State* ret = stateDup( state );
    
    ret->time   -= crossing_time;
    ret->weight += crossing_time;
    
    // Make sure the service period caches are updated if we've traveled over a service period boundary
    int i;
    for(i=0; i<state->n_agencies; i++) {
        if( ret->service_periods[i] && ret->time < ret->service_periods[i]->begin_time) {
          ret->service_periods[i] = ret->service_periods[i]->prev_period;
        }
    }
    
    return ret;
    
}
