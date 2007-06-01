#ifndef _STATETYPES_H_
#define _STATETYPES_H_

#include <stdlib.h>
#include <string.h>

typedef int ServiceId;
typedef struct CalendarDay CalendarDay;

struct CalendarDay {
  long begin_time; //the first second on which the day is valid
  long end_time;   //the last second on which the day is valid
  int n_service_ids;
  ServiceId* service_ids;
  CalendarDay* prev_day;
  CalendarDay* next_day;
} ;


CalendarDay*
calNew( );

CalendarDay*
calAppendDay( CalendarDay* this, long begin_time, long end_time, int n_service_ids, ServiceId* service_ids);

void
calDestroy(CalendarDay* this);

void
calDestroyDay( CalendarDay* this );

int
calDayHasServiceId( CalendarDay* this, ServiceId service_id);

CalendarDay*
calRewind( CalendarDay* this );

CalendarDay*
calFastForward( CalendarDay* this );

CalendarDay*
calDayOfOrAfter( CalendarDay* this, long time );

CalendarDay*
calDayOfOrBefore( CalendarDay* this, long time );
#endif
