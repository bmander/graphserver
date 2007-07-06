#include "statetypes.h"
#include "stdio.h"

//CALENDAR FUNCTIONS

CalendarDay* calNew( long begin_time, long end_time, int n_service_ids, ServiceId* service_ids, int daylight_savings ) {
  CalendarDay* ret = (CalendarDay*)malloc(sizeof(CalendarDay));
  ret->begin_time    = begin_time;
  ret->end_time      = end_time;
  ret->n_service_ids = n_service_ids;
  ret->service_ids  = (ServiceId*)malloc(n_service_ids*sizeof(ServiceId));
  ret->daylight_savings = daylight_savings;
  memcpy( ret->service_ids, service_ids, n_service_ids*sizeof(ServiceId) );
  ret->prev_day = NULL;
  ret->next_day = NULL;

  return ret;
}

//Inserts a new day into the calendar linked list. Pass NULL to create a new linked list
CalendarDay*
calAppendDay( CalendarDay* this, long begin_time, long end_time, int n_service_ids, ServiceId* service_ids, int daylight_savings) {
  CalendarDay* ret = calNew( begin_time, end_time, n_service_ids, service_ids, daylight_savings );

  //if it's a new calendar
  if(!this)
    return ret;

  this->next_day = ret;
  ret->prev_day = this;

  return ret;
}

void
calDestroyDay( CalendarDay* this ) {
  free( this->service_ids );
  free( this );
}

//destroys the calendar linked list given any node on the list
void
calDestroy(CalendarDay* this) {
  CalendarDay* middle = this;
  CalendarDay* trash;

  //delete forward
  this = middle->next_day;
  while(this) {
    trash = this;
    this = trash->next_day;
    calDestroyDay(trash);
  }

  //delete backward
  this = middle->prev_day;
  while(this) {
    trash = this;
    this = trash->prev_day;
    calDestroyDay( trash );
  }

  calDestroyDay( middle );
}
int
calDayHasServiceId( CalendarDay* this, ServiceId service_id) {
  printf("calDayHasServiceId begin\n");
  int i;
  for(i=0; i<this->n_service_ids; i++) {
    if( this->service_ids[i] == service_id ) {
      return 1;
    }
  }
  printf("calDayHasServiceId return\n");
  return 0;
}

CalendarDay*
calRewind( CalendarDay* this ) {
  while( this->prev_day ) {
    this = this->prev_day;
  }
  return this;
}

CalendarDay*
calFastForward( CalendarDay* this ) {
  while( this->next_day ) {
    this = this->next_day;
  }
  return this;
}

CalendarDay*
calDayOfOrAfter( CalendarDay* this, long time ) {
  this = calRewind( this );

  while( this->end_time < time ) {
    this = this->next_day;
    if(!this)
      return NULL;
  }
  return this;
}

CalendarDay*
calDayOfOrBefore( CalendarDay* this, long time ) {
  this = calFastForward( this );

  while( this->begin_time > time ) {
    this = this->prev_day;
    if(!this)
      return NULL;
  }
  return this;
}

void
calPrint( CalendarDay* this ) {
  CalendarDay* curr = calRewind( this );
  while( curr->next_day ) {
    calPrintDay( curr );
    curr = curr->next_day;
  }
}

void
calPrintDay( CalendarDay* this ) {
  printf( "time=%ld..%ld service_ids=[", this->begin_time, this->end_time );
  int i;
  for(i=0; i<this->n_service_ids; i++) {
    printf("%d", this->service_ids[i]);
    if( i != this->n_service_ids-1 )
      printf(", ");
  }
  printf( "]\n" );
}
