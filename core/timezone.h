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
tzPeriodOf( const Timezone* this, long time);

int
tzUtcOffset( const Timezone* this, long time);

int
tzTimeSinceMidnight( const Timezone* this, long time );

TimezonePeriod*
tzHead( const Timezone* this );

void
tzDestroy( Timezone* this );

TimezonePeriod*
tzpNew( long begin_time, long end_time, int utc_offset );

void
tzpDestroy( TimezonePeriod* this );

int
tzpUtcOffset( const TimezonePeriod* this );

int
tzpTimeSinceMidnight( const TimezonePeriod* this, long time );

long
tzpBeginTime( const TimezonePeriod* this );

long
tzpEndTime( const TimezonePeriod* this );

TimezonePeriod*
tzpNextPeriod(const TimezonePeriod* this);

#endif
