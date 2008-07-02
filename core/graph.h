#ifndef GRAPH_H
#define GRAPH_H

#include <stddef.h>
#include <string.h>
#include "hashtable_gs.h"
#include "hashtable_itr.h"
#include "edgetypes.h"

#ifndef INFINITY
  #define INFINITY 1000000000
#endif

typedef struct Vertex Vertex;
typedef struct Edge Edge;
typedef struct ListNode ListNode;
typedef struct Graph Graph;

// the graph data. Major structs
struct Graph {
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
// Vertex
struct Vertex {
   int degree_out;
   int degree_in;
   ListNode* outgoing;
   ListNode* incoming;
   char* label;
   State* payload; //Only used in shortpath
} ;

struct Edge {
  Vertex* from;
  Vertex* to;
  Geom* geom;
  EdgePayload* payload;
} ;

struct ListNode {
   Edge* data;
   ListNode* next;
} ;

//GRAPH FUNCTIONS

Graph*
gNew();

void
gDestroy( Graph* this, int free_vertex_payloads, int free_edge_payloads );

Vertex*
gAddVertex( Graph* this, char *label );

Vertex*
gGetVertex( Graph* this, char *label );

Edge*
gAddEdge( Graph* this, char *from, char *to, EdgePayload *payload );

Edge*
gAddEdgeGeom( Graph* this, char *from, char *to, EdgePayload *payload, char *datageom );

Vertex**
gVertices( Graph* this, long* num_vertices );

Graph*
gShortestPathTree( Graph* this, char *from, char *to, State* init_state );

Graph*
gShortestPathTreeRetro( Graph* this, char *from, char *to, State* init_state );

//direction specifies forward or retro routing
State*
gShortestPath( Graph* this, char *from, char *to, State* init_state, int direction, long *size );

long
gSize( Graph* this );

//VERTEX FUNCTIONS

Vertex *
vNew( char* label ) ;

void
vDestroy(Vertex* this, int free_vertex_payload, int free_edge_payloads) ;

void
vMark(Vertex* this) ;

Edge*
vLink(Vertex* this, Vertex* to, EdgePayload* payload) ;

Edge*
vLinkGeom(Vertex* this, Vertex* to, EdgePayload* payload, char *datageom) ;

Edge*
vSetParent( Vertex* this, Vertex* parent, EdgePayload* payload );
Edge*
vSetParentGeom( Vertex* this, Vertex* parent, EdgePayload* payload, char * geomdata );

inline ListNode*
vGetOutgoingEdgeList( Vertex* this );

inline ListNode*
vGetIncomingEdgeList( Vertex* this );

void
vRemoveOutEdgeRef( Vertex* this, Edge* todie );

void
vRemoveInEdgeRef( Vertex* this, Edge* todie );

//EDGE FUNCTIONS

Edge*
eNew(Vertex* from, Vertex* to, EdgePayload* payload);

Edge*
eNewGeom(Vertex* from, Vertex* to, EdgePayload* payload,char * datageom);

void
eDestroy(Edge *this, int destroy_payload) ;

void
eMark(Edge *this) ;

State*
eWalk(Edge *this, State* params) ;

State*
eWalkBack(Edge *this, State *params) ;

Edge*
eGeom(Edge* this,char * datageom);

//LIST FUNCTIONS

ListNode*
liNew(Edge *data);

void
liInsertAfter( ListNode *this, ListNode *add) ;

void
liRemoveAfter( ListNode *this ) ;

void
liRemoveRef( ListNode *dummyhead, Edge* data );

#endif
