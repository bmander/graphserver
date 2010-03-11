#ifndef _GRAPHSERVER_H_
#define _GRAPHSERVER_H_

typedef struct EdgePayload EdgePayload;
typedef struct State State;
typedef struct ServicePeriod ServicePeriod;
typedef int ServiceId;
typedef struct ServiceCalendar ServiceCalendar;
typedef struct Timezone Timezone;
typedef struct TimezonePeriod TimezonePeriod;
typedef struct WalkOptions WalkOptions;

typedef struct Link Link;

typedef enum {    
  PL_STREET,
  PL_TRIPHOPSCHED_DEPRIC,
  PL_TRIPHOP_DEPRIC,
  PL_LINK,
  PL_EXTERNVALUE,
  PL_NONE, // 5
  PL_WAIT,
  PL_HEADWAY,
  PL_TRIPBOARD,
  PL_CROSSING,
  PL_ALIGHT, // 10
  PL_HEADWAYBOARD,
  PL_EGRESS,
  PL_HEADWAYALIGHT,
  PL_ELAPSE_TIME
} edgepayload_t;

#include "state.h"
#include "edgetypes.h"
#include "walkoptions.h"

#include "link.h"

#endif