#ifndef GRAPH_H
#define GRAPH_H

struct Graph {
   struct hashtable* vertices;
};

struct ShortestPathTree {
   struct hashtable* vertices;
};

//for shortest path trees
struct prev_entry {
  char* from;
  char* to;
  char* desc;
  edgepayload_t type;
  long delta_weight; //DEBUG; not really necessary for anything else
  long weight;
  long end_time;
};

struct Vertex {
   int degree_out;
   int degree_in;
   ListNode* outgoing;
   ListNode* incoming;
   char* label;
    
   int deleted_neighbors;
} ;

struct SPTVertex {
   int degree_out;
   int degree_in;
   ListNode* outgoing;
   ListNode* incoming;
   char* label;
   State* state;
   int hop;
   Vertex *mirror;
} ;

struct Edge {
  Vertex* from;
  Vertex* to;
  EdgePayload* payload;
  int enabled;
} ;

//GRAPH FUNCTIONS

Graph*
gNew(void);

void
gDestroyBasic( Graph* this, int free_edge_payloads );

void
gDestroy( Graph* this );

Vertex*
gAddVertex( Graph* this, char *label );

void
gRemoveVertex( Graph* this, char *label, int free_edge_payloads );

Vertex*
gGetVertex( Graph* this, char *label );

void
gAddVertices( Graph* this, char **labels, int n );

Edge*
gAddEdge( Graph* this, char *from, char *to, EdgePayload *payload );

Vertex**
gVertices( Graph* this, long* num_vertices );

ShortestPathTree*
gShortestPathTree( Graph* this, char *from, char *to, State* init_state, WalkOptions* options, long maxtime, int hoplimit, long weightlimit );

ShortestPathTree*
gShortestPathTreeRetro( Graph* this, char *from, char *to, State* init_state, WalkOptions* options, long mintime, int hoplimit, long weightlimit );

//direction specifies forward or retro routing
State*
gShortestPath( Graph* this, char *from, char *to, State* init_state, int direction, long *size, WalkOptions* options, long timelimit, int hoplimit, long weightlimit );

long
gSize( Graph* this );

void
gSetVertexEnabled( Graph *this, char *label, int enabled );

//SPT METHODS

ShortestPathTree*
sptNew(void);

void
sptDestroy( ShortestPathTree *this );

SPTVertex*
sptAddVertex( ShortestPathTree *this, Vertex *mirror, int hop );

void
sptRemoveVertex( ShortestPathTree *this, char *label );

SPTVertex*
sptGetVertex( ShortestPathTree *this, char *label );

Edge*
sptAddEdge( ShortestPathTree *this, char *from, char *to, EdgePayload *payload );

SPTVertex**
sptVertices( ShortestPathTree *this, long* num_vertices );

long
sptSize( ShortestPathTree* this );

Path *
sptPathRetro(Graph* g, char* origin_label);

//VERTEX FUNCTIONS

Vertex *
vNew( char* label ) ;

void
vDestroy(Vertex* this, int free_edge_payloads) ;

// TODO
//void
//vMark(Vertex* this) ;

Edge*
vLink(Vertex* this, Vertex* to, EdgePayload* payload) ;

Edge*
vSetParent( Vertex* this, Vertex* parent, EdgePayload* payload );

inline ListNode*
vGetOutgoingEdgeList( Vertex* this );

inline ListNode*
vGetIncomingEdgeList( Vertex* this );

void
vRemoveOutEdgeRef( Vertex* this, Edge* todie );

void
vRemoveInEdgeRef( Vertex* this, Edge* todie );

char*
vGetLabel( Vertex* this );

int
vDegreeOut( Vertex* this );

int
vDegreeIn( Vertex* this );

//SPTVERTEX FUNCTIONS

SPTVertex *
sptvNew( Vertex* mirror, int hop ) ;

void
sptvDestroy(SPTVertex* this) ;

Edge*
sptvLink(SPTVertex* this, SPTVertex* to, EdgePayload* payload) ;

Edge*
sptvSetParent( SPTVertex* this, SPTVertex* parent, EdgePayload* payload );

inline ListNode*
sptvGetOutgoingEdgeList( SPTVertex* this );

inline ListNode*
sptvGetIncomingEdgeList( SPTVertex* this );

void
sptvRemoveOutEdgeRef( SPTVertex* this, Edge* todie );

void
sptvRemoveInEdgeRef( SPTVertex* this, Edge* todie );

char*
sptvGetLabel( SPTVertex* this );

int
sptvDegreeOut( SPTVertex* this );

int
sptvDegreeIn( SPTVertex* this );

State*
sptvState( SPTVertex* this );

int
sptvHop( SPTVertex* this );

Edge*
sptvGetParent( SPTVertex* this );

Vertex*
sptvMirror( SPTVertex* this );

//EDGE FUNCTIONS

Edge*
eNew(Vertex* from, Vertex* to, EdgePayload* payload);

void
eDestroy(Edge *this, int destroy_payload) ;

// TODO
//void
//eMark(Edge *this) ;

State*
eWalk(Edge *this, State* state, WalkOptions* options) ;

State*
eWalkBack(Edge *this, State *state, WalkOptions* options) ;

Vertex*
eGetFrom(Edge *this);

Vertex*
eGetTo(Edge *this);

EdgePayload*
eGetPayload(Edge *this);

int
eGetEnabled(Edge *this);

void
eSetEnabled(Edge *this, int enabled);

#endif
