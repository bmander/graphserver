#include <stdint.h>
#include "graphserver.h"

#include "fibheap/fibheap.h"
#include "graph.h"

#include <stddef.h>
#include <string.h>
#include "hashtable/hashtable_gs.h"
#include "hashtable/hashtable_itr.h"

#ifndef INFINITY
  #define INFINITY 1000000000
#endif

const size_t EDGEPAYLOAD_ENUM_SIZE = sizeof(edgepayload_t);

//GRAPH FUNCTIONS

Graph*
gNew() {
  Graph *this = (Graph*)malloc(sizeof(Graph));

  this->n = 0;
  this->cap = INITIAL_GRAPH_CAP;
  this->vertices_store = (Vertex*)malloc( this->cap*sizeof(Vertex) );
  this->vertices = create_hashtable_string(16); //TODO: find a better number.

  this->edge_n = 0;
  this->edge_cap = INITIAL_GRAPH_EDGE_CAP;
  this->edge_store = (Edge*)malloc( this->edge_cap*sizeof(Edge) );

  this->listnode_n = 0;
  this->listnode_cap = INITIAL_GRAPH_LISTNODE_CAP;
  this->listnode_store = (ListNode*)malloc( this->listnode_cap*sizeof(ListNode) );

  return this;
}

void
gDestroyBasic( Graph* this, int free_edge_payloads ) {

  long i;
  for(i=0; i<this->n; i++) {
    vGut( &(this->vertices_store[i]), this, 1 );
  }

  //destroy the table
  hashtable_destroy( this->vertices, 0 );
  //destory vertex store
  free( this->vertices_store );
  //free edge store
  free( this->edge_store );
  //free listnode stroe
  free( this->listnode_store );
  //destroy the graph object itself
  free( this );

}

void
gDestroy( Graph* this ) {
  gDestroyBasic( this, 1 );
}

Vertex*
gAddVertex( Graph* this, char *label ) {

  Vertex* exists = gGetVertex( this, label );

  if( !exists ) {
    exists = &(this->vertices_store[this->n]);
    vInit( exists, this, label );

    hashtable_insert_string( this->vertices, label, this->n );

    this->n++;
    if(this->n >= this->cap) {
        gExpand(this);
    }
  }

  return exists;
}

void
gExpand(Graph *this) {
    this->cap = this->cap*EXPAND_RATIO;
    this->vertices_store = realloc( this->vertices_store, this->cap*sizeof(Vertex) );
}

void
gEdgesExpand(Graph *this) {
    this->edge_cap = this->edge_cap*EXPAND_RATIO;
    this->edge_store = realloc( this->edge_store, this->edge_cap*sizeof(Edge) );
}

void
gRemoveVertex( Graph* this, char *label, int free_edge_payloads ) {
    Vertex *exists = gGetVertex( this, label );
    if(!exists) {
        return;
    }
    
    hashtable_remove( this->vertices, label );
    vGut( exists, this, free_edge_payloads );
}

void 
gAddVertices( Graph* this, char **labels, int n ) {
  int i;
  for (i = 0; i < n; i++) {
  	gAddVertex(this, labels[i]);
  }
}

Vertex*
gGetVertex( Graph* this, char *label ) {
  uint32_t i =  hashtable_search( this->vertices, label );
  return gGetVertexByIndex( this, i );
}

ListNode*
gAllocateListNode( Graph *this, uint32_t data ) {

  //create edge object
  uint32_t ix = this->listnode_n;
  ListNode* ret = &(this->listnode_store[ix]);
  ret->data = data;

  //expand edge vector if necessary
  this->listnode_n++;
  if(this->listnode_n >= this->listnode_cap) {
    this->listnode_cap = this->edge_cap*EXPAND_RATIO;
    this->listnode_store = realloc( this->listnode_store, this->listnode_cap*sizeof(ListNode) );
  }

  return ret;
}

Edge*
gAddEdge( Graph* this, char *from, char *to, EdgePayload *payload ) {
  uint32_t ix_from =  hashtable_search( this->vertices, from );
  Vertex* vtx_from = gGetVertexByIndex( this, ix_from );

  uint32_t ix_to = hashtable_search( this->vertices, to );
  Vertex* vtx_to = gGetVertexByIndex( this, ix_to );

  if(!(vtx_from && vtx_to))
    return NULL;

  //create edge object
  uint32_t link_ix = this->edge_n;
  Edge* link = &(this->edge_store[link_ix]);
  eInit( link, ix_from, ix_to, payload );

  //expand edge vector if necessary
  this->edge_n++;
  if(this->edge_n >= this->edge_cap) {
      gEdgesExpand(this);
  }

  ListNode* outlistnode = liNew( link_ix );
  liInsertAfter( vtx_from->outgoing, outlistnode );
  vtx_from->degree_out++;

  ListNode* inlistnode = liNew( link_ix );
  liInsertAfter( vtx_to->incoming, inlistnode );
  vtx_to->degree_in++;

  return link;
}

Vertex*
gGetVertexByIndex( Graph* this, uint32_t index ) {
  if( index < 0 || index >= this->n ) {
    return NULL;
  }
  
  return &(this->vertices_store[index]);
}

Edge*
gGetEdgeByIndex( Graph *this, uint32_t index ) {
  if( index < 0 || index >= this->edge_n ) {
    return NULL;
  }

  return &(this->edge_store[index]);
}

#undef RETRO
#include "router.c"
#define RETRO
#include "router.c"
#undef RETRO

#define LARGEST_ROUTE_SIZE 10000

State*
gShortestPath( Graph* this, char *from, char *to, State* init_state, int direction, long *size, WalkOptions* options, long timelimit, int hoplimit, long weightlimit ) {
  //make sure from/to vertices exist
  if( !gGetVertex( this, from ) ) {
    fprintf( stderr, "Origin vertex \"%s\" does not exist\n", from );
    return NULL;
  }
  if( !gGetVertex( this, to ) ) {
    fprintf( stderr, "Destination vertex \"%s\" does not exist\n", to );
    return NULL;
  }

  //find minimum spanning tree
  ShortestPathTree *raw_tree;
  SPTVertex *curr;
  if(direction) {
    raw_tree = gShortestPathTree( this, from, to, init_state, options, timelimit, hoplimit, weightlimit );
    curr = sptGetVertex( raw_tree, to );
  } else {
    raw_tree = gShortestPathTreeRetro( this, from, to, init_state, options, timelimit, hoplimit, weightlimit );
    curr = sptGetVertex( raw_tree, from );
  }

  if( !curr ) {
    sptDestroy(raw_tree); //destroy raw_table and contents, as they won't be used
    fprintf( stderr, "Destination vertex never reached\n" );
    return NULL;
  }

  //TODO: replace ret with a resizeable array
  State *temppath = (State*)malloc(LARGEST_ROUTE_SIZE*sizeof(State));


  int i=0;
  while( curr ) {
    if( i > LARGEST_ROUTE_SIZE ) {         //Bail if our crude memory management techniques fail
      sptDestroy( raw_tree );
      free(temppath);
      fprintf( stderr, "Route %d hops long, larger than preallocated %d hops\n", i, LARGEST_ROUTE_SIZE );
      return NULL;
    }

    temppath[i] = *((State*)(curr->state));
    i++;

    if( curr->parentedge == LI_NO_DATA )
      break;
    else {
      uint32_t parent_ix = curr->parentedge;
      SPTEdge *parent = sptGetEdgeByIndex( raw_tree, parent_ix );
      curr = parent->from;
    }
  }

  int n = i;
  //reverse path while copying to a newly allocated set of prev_entries
  State *ret = (State*)malloc(n*sizeof(State));
  //path need not be reversed in the case of a retro route; the tree trace started at the beginning
  if(direction) {
    i=0;
    int j=n-1;
    for( ; i<n; ) {
      ret[i] = temppath[j];
      i++;
      j--;
    }
  } else {
    //memcpy would be faster
    for(i=0; i<n; i++) {
      ret[i] = temppath[i];
    }
  }
  free( temppath );

  //destroy vertex payloads - we've transferred the relevant state information out
  //do not destroy the edge payloads - they belong to the creating graph
  //TODO: fix this so memory stops leaking:
  //gDestroy( raw_tree, 1, 0 );

  //return
  *size = n;
  return ret;
}

Path *
sptPathRetro(ShortestPathTree* spt, char* origin_label) {
  SPTVertex* curr = sptGetVertex(spt, origin_label);
  ListNode* incoming = NULL;
  SPTEdge* edge = NULL;
    
  if (!curr) return NULL;

  Path *path = pathNew(curr, 50, 50);

  // trace backwards up the tree until the current vertex has no parents
  while (curr->parentedge != LI_NO_DATA) {
    edge = sptGetEdgeByIndex( spt, curr->parentedge );
    curr = spteGetFrom(edge);
        
    pathAddSegment( path, curr, edge );
  }

  return path;	
}

long
gSize( Graph* this ) {
  return hashtable_count( this->vertices );
}

void
gSetVertexEnabled( Graph *this, char *label, int enabled ) {
    
    Vertex *vv = gGetVertex( this, label );
    
    ListNode* outgoing_edge_node = vGetOutgoingEdgeList( vv );

    while(outgoing_edge_node) {
        eSetEnabled( gGetEdgeByIndex( this, outgoing_edge_node->data ), enabled );
        outgoing_edge_node = outgoing_edge_node->next;
    }

    ListNode* incoming_edge_node = vGetIncomingEdgeList( vv );

    while(incoming_edge_node) {
        eSetEnabled( gGetEdgeByIndex( this, incoming_edge_node->data ), enabled );
        incoming_edge_node = incoming_edge_node->next;
    }
    
}

// SPT METHODS

ShortestPathTree*
sptNew() {
    return (ShortestPathTree*)gNew();
}

void
sptDestroy( ShortestPathTree *this ) {

  //destroy each vertex contained within
  uint32_t i = 0;
  for(i=0; i<this->n; i++) {
    sptvGut( &(this->vertices_store[i]), this );
  }

  //destroy the table
  hashtable_destroy( this->vertices, 0 );
  //destory vertex store
  free( this->vertices_store );
  //free edge store
  free( this->edge_store );
  //destroy the graph object itself
  free( this );
}

ListNode*
sptAllocateListNode( ShortestPathTree *this, uint32_t data ) {
    return gAllocateListNode( (Graph*)this, data );
}

SPTVertex*
sptAddVertex( ShortestPathTree *this, Vertex *mirror, int hop ) {
  SPTVertex* exists = sptGetVertex( this, mirror->label );

  if( !exists ) {
    exists = &(this->vertices_store[this->n]);
    sptvInit( exists, this, mirror, hop );

    hashtable_insert_string( this->vertices, mirror->label, this->n );

    this->n++;
    if(this->n >= this->cap) {
        sptExpand(this);
    }
  }

  return exists;
}

void
sptExpand(ShortestPathTree *this) {
    this->cap = this->cap*EXPAND_RATIO;
    this->vertices_store = realloc( this->vertices_store, this->cap*sizeof(SPTVertex) );
}

void
sptEdgesExpand(ShortestPathTree *this) {
    this->edge_cap = this->edge_cap*EXPAND_RATIO;
    this->edge_store = realloc( this->edge_store, this->edge_cap*sizeof(Edge) );
}

void
sptRemoveVertex( ShortestPathTree *this, char *label ) {
    SPTVertex *exists = sptGetVertex( this, label );
    if(!exists) {
        return;
    }
    
    hashtable_remove( this->vertices, label );
    sptvGut( exists, this );
}

SPTVertex*
sptGetVertexByIndex( ShortestPathTree* this, uint32_t index ) {
  if( index < 0 || index >= this->n ) {
    return NULL;
  }
  
  return &(this->vertices_store[index]);
}

SPTEdge*
sptGetEdgeByIndex( ShortestPathTree *this, uint32_t index ) {
  if( index < 0 || index >= this->edge_n ) {
    return NULL;
  }

  return &(this->edge_store[index]);
}

SPTVertex*
sptGetVertex( ShortestPathTree *this, char *label ) {
    uint32_t i =  hashtable_search( this->vertices, label );
    return sptGetVertexByIndex( this, i );
}

SPTEdge*
sptSetParent( ShortestPathTree *this, char *from, char *to, EdgePayload *payload ) {
  SPTVertex* vtx_from = sptGetVertex( this, from );
  SPTVertex* vtx_to   = sptGetVertex( this, to );

  if(!(vtx_from && vtx_to))
    return NULL;

  return sptvSetParent( this, vtx_to, vtx_from, payload );
}

long
sptSize( ShortestPathTree* this ) {
    return gSize( (Graph*)this );
}


// VERTEX FUNCTIONS

void vInit( Vertex *this, Graph *gg, char *label ) {
    this->degree_in = 0;
    this->degree_out = 0;
    this->outgoing = liNew( LI_NO_DATA ) ;
    this->incoming = liNew( LI_NO_DATA ) ;
    
    this->deleted_neighbors = 0;

    strcpy(this->label, label);
}

Vertex *
vNew( Graph *gg, char* label ) {
    Vertex *this = (Vertex *)malloc(sizeof(Vertex)) ;

    vInit( this, gg, label );


    return this ;
}

void
vGut(Vertex *this, Graph* gg, int free_edge_payloads) {
    if( gg ) {
      //delete incoming edges
      while(this->incoming->next != NULL) {
        eDestroy( gGetEdgeByIndex( gg, this->incoming->next->data ), gg, this->incoming->next->data, free_edge_payloads );
      }
      //delete outgoing edges
      while(this->outgoing->next != NULL) {
        eDestroy( gGetEdgeByIndex( gg, this->outgoing->next->data ), gg, this->outgoing->next->data, free_edge_payloads );
      }
    }
    //free the list dummy-heads that remain
    free(this->outgoing);
    free(this->incoming);

    //set incoming and outgoing to NULL to signify that this has been gutted
    this->outgoing = NULL;
    this->incoming = NULL;

}

void
vDestroy(Vertex *this, int free_edge_payloads) {

    vGut( this, NULL, free_edge_payloads );

    //and finally, sweet release*/
    free( this );
}

ListNode*
vGetOutgoingEdgeList( Vertex* this ) {
    return this->outgoing->next; //the first node is a dummy
}

ListNode*
vGetIncomingEdgeList( Vertex* this ) {
    return this->incoming->next; //the first node is a dummy
}

void
vRemoveOutEdgeRef( Vertex* this, uint32_t todie ) {
    this->degree_out -= 1;
    liRemoveRef( this->outgoing, todie );
}

void
vRemoveInEdgeRef( Vertex* this, uint32_t todie ) {
    this->degree_in -= 1;
    liRemoveRef( this->incoming, todie );
}

char*
vGetLabel( Vertex* this ) {
    return this->label;
}

int
vDegreeOut( Vertex* this ) {
    return this->degree_out;
}

int
vDegreeIn( Vertex* this ) {
    return this->degree_in;
}

//SPTVERTEX METHODS

void
sptvInit( SPTVertex* this, ShortestPathTree *spt, Vertex* mirror, int hop ) {
    this->degree_out = 0;
    this->outgoing = liNew( LI_NO_DATA ) ;
    this->parentedge = LI_NO_DATA;
    
    this->state = NULL;
    this->fibnode = NULL;
    this->hop = hop;
    this->mirror = mirror;
}

SPTVertex *
sptvNew( ShortestPathTree *spt, Vertex* mirror, int hop ) {
    SPTVertex *this = (SPTVertex *)malloc(sizeof(SPTVertex));

    sptvInit( this, spt, mirror, hop );
    
    return this;
}

void
sptvGut( SPTVertex* this, ShortestPathTree *spt ) {
    //delete outgoing edges
    while(this->outgoing->next != NULL) {
      uint32_t next_edge_ix = this->outgoing->next->data;
      SPTEdge *next_edge = sptGetEdgeByIndex( spt, next_edge_ix );
      spteDestroy( next_edge, next_edge_ix );
    }

    //free the list dummy-heads that remain
    free(this->outgoing);

    //set incoming and outgoing to NULL to signify that this has been gutted
    this->outgoing = NULL;
    this->parentedge = LI_NO_DATA;
}

void
sptvDestroy(SPTVertex* this, ShortestPathTree *spt) {
    if( this->state ) {
        stateDestroy( this->state );
    }

    sptvGut( this, spt );

    free( this );
}

SPTEdge*
sptvSetParent( ShortestPathTree *spt, SPTVertex* this, SPTVertex* parent, EdgePayload* payload ) {
    //disconnect parent edge from parent
    if( this->parentedge != LI_NO_DATA ) {
        sptvRemoveOutEdgeRef( sptGetEdgeByIndex(spt, this->parentedge)->from, this->parentedge );
    }

    //create edge object
    uint32_t link_ix = spt->edge_n;
    SPTEdge* link = &(spt->edge_store[link_ix]);
    spteInit( link, parent, this, payload );

    //expand edge vector if necessary
    spt->edge_n++;
    if(spt->edge_n >= spt->edge_cap) {
      sptEdgesExpand(spt);
    }

    //add it to the outgoing list of the parent
    ListNode* outlistnode = liNew( link_ix );
    liInsertAfter( parent->outgoing, outlistnode );
    parent->degree_out++;

    //set it as the parent of the child
    this->parentedge = link_ix;

    return link;
}

inline ListNode*
sptvGetOutgoingEdgeList( SPTVertex* this ) {
    return this->outgoing->next; //the first node is a dummy
}

void
sptvRemoveOutEdgeRef( SPTVertex* this, uint32_t todie ) {
    this->degree_out -= 1;
    liRemoveRef( this->outgoing, todie );
}

int
sptvDegreeOut( SPTVertex* this ) {
    return this->degree_out;
}

State*
sptvState( SPTVertex* this ) {
    return this->state;
}

int
sptvHop( SPTVertex* this ) {
    return this->hop;
}

uint32_t
sptvGetParent( SPTVertex* this ) {
    return this->parentedge;
}

Vertex*
sptvMirror( SPTVertex* this ) {
    return this->mirror;
}

// EDGE FUNCTIONS

void
eInit(Edge *this, uint32_t from, uint32_t to, EdgePayload *payload) {
    this->from = from;
    this->to = to;
    this->payload = payload;
    this->enabled = 1;
}

Edge*
eNew(uint32_t from, uint32_t to, EdgePayload* payload) {
    Edge *this = (Edge *)malloc(sizeof(Edge));
    eInit( this, from, to, payload );
    return this;
}

void
eDestroy(Edge *this, Graph* gg, uint32_t index, int destroy_payload) {
    //free payload
    if(destroy_payload)
      epDestroy( this->payload ); //destroy payload object and contents

    Vertex* fromv = gGetVertexByIndex( gg, this->from );
    Vertex* tov = gGetVertexByIndex( gg, this->to );

    vRemoveOutEdgeRef( fromv, index );
    vRemoveInEdgeRef( tov, index );
}

State*
eWalk(Edge *this, State* state, WalkOptions* options) {
  if( this->enabled ) {
    return epWalk( this->payload, state, options );
  } else {
    return NULL;
  }
}

State*
eWalkBack(Edge *this, State* state, WalkOptions* options) {
  if( this->enabled ) {
    return epWalkBack( this->payload, state, options );
  } else {
    return NULL;
  }
}

uint32_t
eGetFrom(Edge *this) {
  return this->from;
}

uint32_t
eGetTo(Edge *this) {
  return this->to;
}

EdgePayload*
eGetPayload(Edge *this) {
  return this->payload;
}

int
eGetEnabled(Edge *this) {
    return this->enabled;
}

void
eSetEnabled(Edge *this, int enabled) {
    this->enabled = enabled;
}

// SPTEDGE FUNCTIONS

void
spteInit(SPTEdge *this, SPTVertex *from, SPTVertex *to, EdgePayload *payload) {
    this->from = from;
    this->to = to;
    this->payload = payload;
}

SPTEdge*
spteNew(SPTVertex* from, SPTVertex* to, EdgePayload* payload) {
    SPTEdge *this = (SPTEdge *)malloc(sizeof(SPTEdge));
    spteInit( this, from, to, payload );
    return this;
}

void
spteDestroy(SPTEdge *this, uint32_t this_ix) {
    this->from->degree_out -= 1;
    liRemoveRef( this->from->outgoing, this_ix );
}

SPTVertex*
spteGetFrom(SPTEdge *this) {
  return this->from;
}

SPTVertex*
spteGetTo(SPTEdge *this) {
  return this->to;
}

EdgePayload*
spteGetPayload(SPTEdge *this) {
  return this->payload;
}
