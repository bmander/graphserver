#ifndef _GRAPHSERVER_H_
#define _GRAPHSERVER_H_

#define ABSOLUTE_MAX_WALK 1000000 //meters. 100 km. prevents overflow
#define MAX_LONG 2147483647
#define INFINITY MAX_LONG
#define SECS_IN_DAY 86400
#define TRUE 1
#define FALSE 0

typedef int ServiceId;

// generally useful classes
typedef struct EdgePayload EdgePayload;
typedef struct State State;
typedef struct WalkOptions WalkOptions;
typedef struct Vertex Vertex;
typedef struct Edge Edge;
typedef struct ListNode ListNode;
typedef struct Graph Graph;
typedef struct Path Path;
typedef struct Vector Vector;
typedef struct SPTVertex SPTVertex;
typedef struct ShortestPathTree ShortestPathTree;

// classes that support edgetypes
typedef struct ServicePeriod ServicePeriod;
typedef struct ServiceCalendar ServiceCalendar;
typedef struct Timezone Timezone;
typedef struct TimezonePeriod TimezonePeriod;

// edgetypes
typedef struct Link Link;
typedef struct Street Street;
typedef struct Egress Egress;
typedef struct Wait Wait;
typedef struct ElapseTime ElapseTime;
typedef struct Headway Headway;
typedef struct TripBoard TripBoard;
typedef struct HeadwayBoard HeadwayBoard;
typedef struct HeadwayAlight HeadwayAlight;
typedef struct Crossing Crossing;
typedef struct TripAlight TripAlight;
typedef struct Combination Combination;
typedef struct CHPath CHPath;
typedef struct CH CH;
typedef struct Heap Heap;
typedef struct HeapNode HeapNode;

typedef struct PayloadMethods PayloadMethods;
typedef struct CustomPayload CustomPayload;

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
  PL_ELAPSE_TIME,
  PL_COMBINATION
} edgepayload_t;

#include "state.h"
#include "walkoptions.h"
#include "edgetypes/elapsehelpers.h"

#include "edgetypes/link.h"
#include "edgetypes/street.h"
#include "edgetypes/egress.h"
#include "edgetypes/wait.h"
#include "edgetypes/elapsetime.h"
#include "edgetypes/headway.h"
#include "edgetypes/tripboard.h"
#include "edgetypes/headwayboard.h"
#include "edgetypes/headwayalight.h"
#include "edgetypes/crossing.h"
#include "edgetypes/tripalight.h"
#include "edgetypes/custompayload.h"
#include "edgetypes/combination.h"
#include "edgepayload.h"
#include "list.h"
#include "servicecalendar.h"
#include "timezone.h"
#include "path.h"
#include "vector.h"
#include "heap.h"

// things that everyone needs
#include <stdlib.h>
#include <string.h>

#endif
