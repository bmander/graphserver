#define ABSOLUTE_MAX_WALK 1000000 //meters. 100 km. prevents overflow
#define MAX_LONG 2147483647
#define SECS_IN_DAY 86400

#ifndef ROUTE_REVERSE
#define ELAPSE_TIME_AND_SERVICE_PERIOD(ret, delta_t) \
  int i; \
  ret->time           += delta_t; \
  for(i=0; i<state->n_agencies; i++) { \
      ServicePeriod* sp = state->service_periods[i]; \
      if(sp && ret->time >= sp->end_time) { \
        ret->service_periods[i] = sp->next_period; \
      } \
  }
#else
#define ELAPSE_TIME_AND_SERVICE_PERIOD(ret, delta_t) \
  int i; \
  ret->time           -= delta_t; \
  for(i=0; i<state->n_agencies; i++) { \
    ServicePeriod* sp = state->service_periods[i]; \
    if(sp && ret->time < sp->begin_time) { \
      ret->service_periods[i] = sp->prev_period; \
    } \
  }
#endif

