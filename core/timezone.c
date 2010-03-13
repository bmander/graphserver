
#include "graphserver.h"

Timezone*
tzNew( ) {
    Timezone* ret = (Timezone*)malloc(sizeof(Timezone));
    ret->head = NULL;
    
    return ret;
}

void
tzAddPeriod( Timezone* this, TimezonePeriod* period ) {
    if(!this->head) {
        this->head = period;
    } else {
        TimezonePeriod* prev = NULL;
        TimezonePeriod* curs = this->head;
        
        while(curs && period->begin_time > curs->end_time ) {
            prev = curs;
            curs = curs->next_period;
        }
        
        //link last and period; replace the head if necessary
        if(prev) {
            prev->next_period = period;
        } else {
            this->head = period;
        }
        
        //link period and curs
        period->next_period = curs;
        
    }
}

TimezonePeriod*
tzPeriodOf( Timezone* this, long time) {
  TimezonePeriod* period = this->head;

  while( period && period->end_time < time ) {
    period = period->next_period;
  }
  
  if( period && time < period->begin_time ) {
      return NULL;
  }
  
  return period;
}

int
tzUtcOffset( Timezone* this, long time) {
    //Returns seconds offset UTC for this timezone, at the given time
    
    TimezonePeriod* now = tzPeriodOf( this, time );
    
    if( !now ) {
        return -100*3600; //utc offset larger than any conceivable offset, as an error signal
    }
    
    return tzpUtcOffset( now );
}

int
tzTimeSinceMidnight( Timezone* this, long time ) {
    TimezonePeriod* now = tzPeriodOf( this, time );
    
    if( !now ) {
        return -1;
    }
    
    return (time+now->utc_offset)%SECS_IN_DAY;
}

TimezonePeriod*
tzHead( Timezone* this ) {
    return this->head;
}

void
tzDestroy( Timezone* this ) {
    TimezonePeriod* curs = this->head;
    TimezonePeriod* next;

    while(curs) {
      next = curs->next_period;
      tzpDestroy(curs);
      curs = next;
    }

    free(this);
}

TimezonePeriod*
tzpNew( long begin_time, long end_time, int utc_offset ) {
    TimezonePeriod* ret = (TimezonePeriod*)malloc(sizeof(TimezonePeriod));
    ret->begin_time    = begin_time;
    ret->end_time      = end_time;
    ret->utc_offset    = utc_offset;
    ret->next_period = NULL;

    return ret;
}

void
tzpDestroy( TimezonePeriod* this ) {
    free( this );
}

int
tzpUtcOffset( TimezonePeriod* this ) {
    return this->utc_offset;
}

int
tzpTimeSinceMidnight( TimezonePeriod* this, long time ) {
    return (time+this->utc_offset)%SECS_IN_DAY;
}

long
tzpBeginTime( TimezonePeriod* this ) {
    return this->begin_time;
}

long
tzpEndTime( TimezonePeriod* this ) {
    return this->end_time;
}

TimezonePeriod*
tzpNextPeriod(TimezonePeriod* this) {
    return this->next_period;
}