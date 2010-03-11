//---------------DECLARATIONS FOR STREET  CLASS---------------------

typedef struct Street {
   edgepayload_t type;
   State* (*walk)(struct EdgePayload*, struct State*, struct WalkOptions*);
   State* (*walkBack)(struct EdgePayload*, struct State*, struct WalkOptions*);
    
   char* name;
   double length;
   float rise;
   float fall;
   float slog;
   long way;
} Street;

Street*
streetNew(const char *name, double length);

Street*
streetNewElev(const char *name, double length, float rise, float fall);

void
streetDestroy(Street* tokill);

inline State*
streetWalk(EdgePayload* superthis, State* state, WalkOptions* options);

inline State*
streetWalkBack(EdgePayload* superthis, State* state, WalkOptions* options);

char*
streetGetName(Street* this);

double
streetGetLength(Street* this);

float
streetGetRise(Street* this);

float
streetGetFall(Street* this);

void
streetSetRise(Street* this, float rise) ;

void
streetSetFall(Street* this, float fall) ;

long
streetGetWay(Street* this);

void
streetSetWay(Street* this, long way);