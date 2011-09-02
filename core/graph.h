#ifndef GRAPH_H
#define GRAPH_H

#define INITIAL_GRAPH_CAP 2048
#define INITIAL_GRAPH_EDGE_CAP 2048
#define INITIAL_GRAPH_LISTNODE_CAP 2048
#define EXPAND_RATIO 1.5

struct Graph {
    uint32_t n;
    uint32_t cap;
    Vertex* vertices_store;

    uint32_t edge_n;
    uint32_t edge_cap;
    Edge* edge_store;

    uint32_t listnode_n;
    uint32_t listnode_cap;
    ListNode *listnode_store;

    struct hashtable* vertices;
};

struct ShortestPathTree {
    long int n;
    long int cap;
    SPTVertex* vertices_store;

    uint32_t edge_n;
    uint32_t edge_cap;
    SPTEdge* edge_store;

    uint32_t listnode_n;
    uint32_t listnode_cap;
    ListNode *listnode_store;

    struct hashtable* vertices;
};

struct Vertex {
   int degree_out;
   int degree_in;
   ListNode* outgoing;
   ListNode* incoming;
   char label[50];
    
   int deleted_neighbors;
} ;

struct SPTVertex {
   int degree_out;
   ListNode* outgoing;
   uint32_t parentedge;

   State* state;
   int hop;
   Vertex *mirror;
   fibnode_t fibnode;
} ;

struct Edge {
  uint32_t from;
  uint32_t to;
  EdgePayload* payload;
  int enabled;

  uint32_t next;
} ;

struct SPTEdge {
  SPTVertex* from;
  SPTVertex* to;
  EdgePayload* payload;
} ;

//GRAPH FUNCTIONS

Graph*
gNew(void);

void
gDestroyBasic( Graph* this, int free_edge_payloads );

void
gDestroy( Graph* this );

void
gExpand( Graph *this );

ListNode*
gAllocateListNode( Graph *this, uint32_t data ) ;

Vertex*
gAddVertex( Graph* this, char *label );

void
gRemoveVertex( Graph* this, char *label, int free_edge_payloads );

uint32_t
gGetVertexIndex( Graph *this, char *label );

Vertex*
gGetVertex( Graph* this, char *label );

void
gAddVertices( Graph* this, char **labels, int n );

Edge*
gAddEdge( Graph* this, char *from, char *to, EdgePayload *payload );

Vertex*
gGetVertexByIndex( Graph* this, uint32_t index );

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

void
sptExpand(ShortestPathTree *this); 

ListNode*
sptAllocateListNode( ShortestPathTree *this, uint32_t data ) ;

uint32_t
sptAddVertexIndex( ShortestPathTree *this, Vertex *mirror, int hop );

SPTVertex*
sptAddVertex( ShortestPathTree *this, Vertex *mirror, int hop );

void
sptRemoveVertex( ShortestPathTree *this, char *label );

uint32_t
sptGetVertexIndex( ShortestPathTree *this, char *label );

SPTVertex*
sptGetVertex( ShortestPathTree *this, char *label );

SPTEdge*
sptGetEdgeByIndex( ShortestPathTree *this, uint32_t index );

SPTEdge*
sptSetParent( ShortestPathTree *this, char *from, char *to, EdgePayload *payload );

SPTVertex**
sptVertices( ShortestPathTree *this, long* num_vertices );

long
sptSize( ShortestPathTree* this );

Path *
sptPathRetro(ShortestPathTree* g, char* origin_label);

//VERTEX FUNCTIONS

Vertex *
vNew( Graph *gg, char* label ) ;

void
vInit( Vertex *this, Graph *gg, char *label );

void
vGut(Vertex *this, Graph *gg, int free_edge_payloads);

void
vDestroy(Vertex* this, int free_edge_payloads) ;

inline ListNode*
vGetOutgoingEdgeList( Vertex* this );

inline ListNode*
vGetIncomingEdgeList( Vertex* this );

void
vRemoveOutEdgeRef( Vertex* this, uint32_t todie );

void
vRemoveInEdgeRef( Vertex* this, uint32_t todie );

char*
vGetLabel( Vertex* this );

int
vDegreeOut( Vertex* this );

int
vDegreeIn( Vertex* this );

//SPTVERTEX FUNCTIONS

void
sptvInit( SPTVertex* this, ShortestPathTree *spt, Vertex* mirror, int hop );

SPTVertex *
sptvNew( ShortestPathTree *spt, Vertex* mirror, int hop ) ;

void
sptvGut( SPTVertex* this, ShortestPathTree *spt ) ;

void
sptvDestroy(SPTVertex* this, ShortestPathTree *spt) ;

SPTEdge*
sptvLink(SPTVertex* this, SPTVertex* to, EdgePayload* payload) ;

SPTEdge*
sptvSetParent( ShortestPathTree* spt, SPTVertex* this, SPTVertex* parent, EdgePayload* payload );

inline ListNode*
sptvGetOutgoingEdgeList( SPTVertex* this );

void
sptvRemoveOutEdgeRef( SPTVertex* this, uint32_t todie );

char*
sptvGetLabel( SPTVertex* this );

int
sptvDegreeOut( SPTVertex* this );

State*
sptvState( SPTVertex* this );

int
sptvHop( SPTVertex* this );

uint32_t
sptvGetParent( SPTVertex* this );

Vertex*
sptvMirror( SPTVertex* this );

//EDGE FUNCTIONS

void
eInit(Edge* this, uint32_t from, uint32_t to, EdgePayload *payload) ;

Edge*
eNew(uint32_t from, uint32_t to, EdgePayload* payload);

void
eDestroy(Edge *this, Graph* gg, uint32_t index, int destroy_payload) ;

State*
eWalk(Edge *this, State* state, WalkOptions* options) ;

State*
eWalkBack(Edge *this, State *state, WalkOptions* options) ;

uint32_t
eGetFrom(Edge *this);

uint32_t
eGetTo(Edge *this);

EdgePayload*
eGetPayload(Edge *this);

int
eGetEnabled(Edge *this);

void
eSetEnabled(Edge *this, int enabled);

//SPTEDGE FUNCTIONS

void
spteInit(SPTEdge *this, SPTVertex *from, SPTVertex *to, EdgePayload *payload);

SPTEdge*
spteNew(SPTVertex* from, SPTVertex* to, EdgePayload* payload);

void
spteDestroy(SPTEdge *this, uint32_t this_ix) ;

SPTVertex*
spteGetFrom(SPTEdge *this);

SPTVertex*
spteGetTo(SPTEdge *this);

EdgePayload*
spteGetPayload(SPTEdge *this);

#endif
