#include "../graphserver.h"

void elapse_time_and_service_period_forward(State *ret, State *state, long delta_t) {
  int i; 
  ret->time           += delta_t; 
  for(i=0; i<state->n_agencies; i++) { 
      ServicePeriod* sp = state->service_periods[i]; 
      if(sp && ret->time >= sp->end_time) { 
        ret->service_periods[i] = sp->next_period; 
      } 
  }
}

void elapse_time_and_service_period_backward(State *ret, State *state, long delta_t) {
  int i; 
  ret->time           -= delta_t; 
  for(i=0; i<state->n_agencies; i++) { 
    ServicePeriod* sp = state->service_periods[i]; 
    if(sp && ret->time < sp->begin_time) { 
      ret->service_periods[i] = sp->prev_period; 
    } 
  }
}