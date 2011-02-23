#ifndef _TIMEZONE_H_
#define _TIMEZONE_H_

struct TimezonePeriod {
  long begin_time; //the first second on which the service_period is valid
  long end_time;   //the last second on which the service_period is valid
  int utc_offset;
  TimezonePeriod* next_period;
} ;

struct Timezone {
    TimezonePeriod* head;
} ; 

Timezone*
tzNew(void);

void
tzAddPeriod( Timezone* this, TimezonePeriod* period );

TimezonePeriod*
tzPeriodOf( Timezone* this, long time);

int
tzUtcOffset( Timezone* this, long time);

int
tzTimeSinceMidnight( Timezone* this, long time );

TimezonePeriod*
tzHead( Timezone* this );

void
tzDestroy( Timezone* this );

TimezonePeriod*
tzpNew( long begin_time, long end_time, int utc_offset );

void
tzpDestroy( TimezonePeriod* this );

int
tzpUtcOffset( TimezonePeriod* this );

int
tzpTimeSinceMidnight( TimezonePeriod* this, long time );

long
tzpBeginTime( TimezonePeriod* this );

long
tzpEndTime( TimezonePeriod* this );

TimezonePeriod*
tzpNextPeriod(TimezonePeriod* this);

#endif
