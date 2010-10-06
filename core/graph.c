#include "graphserver.h"

#include "graph.h"
#include "fibheap/fibheap.h"
#include "fibheap/dirfibheap.h"

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
  this->vertices = create_hashtable_string(16); //TODO: find a better number.

  return this;
}

void
gDestroyBasic( Graph* this, int free_edge_payloads ) {

  //destroy each vertex contained within
  struct hashtable_itr *itr = hashtable_iterator(this->vertices);
  int next_exists = hashtable_count(this->vertices);

  while(itr && next_exists) {
    Vertex* vtx = hashtable_iterator_value( itr );
    vDestroy( vtx, 1 );
    next_exists = hashtable_iterator_advance( itr );
  }

  free(itr);
  //destroy the table
  hashtable_destroy( this->vertices, 0 );
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
    exists = vNew( label );
    hashtable_insert_string( this->vertices, label, exists );
  }

  return exists;
}

void
gRemoveVertex( Graph* this, char *label, int free_edge_payloads ) {
    Vertex *exists = gGetVertex( this, label );
    if(!exists) {
        return;
    }
    
    hashtable_remove( this->vertices, label );
    vDestroy( exists, free_edge_payloads );
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
  return hashtable_search( this->vertices, label );
}

Edge*
gAddEdge( Graph* this, char *from, char *to, EdgePayload *payload ) {
  Vertex* vtx_from = gGetVertex( this, from );
  Vertex* vtx_to   = gGetVertex( this, to );

  if(!(vtx_from && vtx_to))
    return NULL;

  return vLink( vtx_from, vtx_to, payload );
}

Vertex**
gVertices( Graph* this, long* num_vertices ) {
  unsigned int nn = hashtable_count(this->vertices);
  Vertex** ret = (Vertex**)malloc(nn*sizeof(Vertex*));

  long i=0;
  struct hashtable_itr *itr = hashtable_iterator(this->vertices);
  int next_exists=nn; //next_exists is false when number of vertices is 0

  while(itr && next_exists) {
    Vertex* vtx = hashtable_iterator_value( itr );
    ret[i] = vtx;
    next_exists = hashtable_iterator_advance( itr );
    i++;
  }
  
  free(itr);

  *num_vertices = nn;
  return ret;
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

    if( curr->degree_in == 0 )
      break;
    else
      curr = (SPTVertex*)sptvGetIncomingEdgeList( curr )->data->from;
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
sptPathRetro(Graph* g, char* origin_label) {
  Vertex* curr = gGetVertex(g, origin_label);
  ListNode* incoming = NULL;
  Edge* edge = NULL;
    
  if (!curr) return NULL;

  Path *path = pathNew(curr, 50, 50);
	
  // trace backwards up the tree until the current vertex has no parents
  while ((incoming = vGetIncomingEdgeList(curr))) {
        
    edge = liGetData(incoming);
    curr = eGetFrom(edge);
        
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
        eSetEnabled( outgoing_edge_node->data, enabled );
        outgoing_edge_node = outgoing_edge_node->next;
    }

    ListNode* incoming_edge_node = vGetIncomingEdgeList( vv );

    while(incoming_edge_node) {
        eSetEnabled( incoming_edge_node->data, enabled );
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
  struct hashtable_itr *itr = hashtable_iterator(this->vertices);
  int next_exists = hashtable_count(this->vertices);

  while(itr && next_exists) {
    SPTVertex* vtx = hashtable_iterator_value( itr );
    sptvDestroy( vtx );
    next_exists = hashtable_iterator_advance( itr );
  }

  free(itr);
  //destroy the table
  hashtable_destroy( this->vertices, 0 );
  //destroy the graph object itself
  free( this );
}

SPTVertex*
sptAddVertex( ShortestPathTree *this, Vertex *mirror, int hop ) {
  SPTVertex* exists = sptGetVertex( this, mirror->label );
  if( !exists ) {
    exists = sptvNew( mirror, hop );
    hashtable_insert_string( this->vertices, mirror->label, exists );
  }

  return exists;
}

void
sptRemoveVertex( ShortestPathTree *this, char *label ) {
    SPTVertex *exists = sptGetVertex( this, label );
    if(!exists) {
        return;
    }
    
    hashtable_remove( this->vertices, label );
    sptvDestroy( exists );
}

SPTVertex*
sptGetVertex( ShortestPathTree *this, char *label ) {
    return (SPTVertex*)gGetVertex( (Graph*)this, label );
}

Edge*
sptAddEdge( ShortestPathTree *this, char *from, char *to, EdgePayload *payload ) {
  SPTVertex* vtx_from = sptGetVertex( this, from );
  SPTVertex* vtx_to   = sptGetVertex( this, to );

  if(!(vtx_from && vtx_to))
    return NULL;

  return sptvLink( vtx_from, vtx_to, payload );
}

SPTVertex**
sptVertices( ShortestPathTree *this, long* num_vertices ) {
    return (SPTVertex**)gVertices( (Graph*)this, num_vertices );
}

long
sptSize( ShortestPathTree* this ) {
    return gSize( (Graph*)this );
}


// VERTEX FUNCTIONS

void vInit( Vertex *this, char *label ) {
    this->degree_in = 0;
    this->degree_out = 0;
    this->outgoing = liNew( NULL ) ;
    this->incoming = liNew( NULL ) ;
    
    this->deleted_neighbors = 0;

    size_t labelsize = strlen(label)+1;
    this->label = (char*)malloc(labelsize*sizeof(char));
    strcpy(this->label, label);
}

Vertex *
vNew( char* label ) {
    Vertex *this = (Vertex *)malloc(sizeof(Vertex)) ;

    vInit( this, label );


    return this ;
}

void
vDestroy(Vertex *this, int free_edge_payloads) {

    //delete incoming edges
    while(this->incoming->next != NULL) {
      eDestroy( this->incoming->next->data, free_edge_payloads );
    }
    //delete outgoing edges
    while(this->outgoing->next != NULL) {
      eDestroy( this->outgoing->next->data, free_edge_payloads );
    }
    //free the list dummy-heads that remain
    free(this->outgoing);
    free(this->incoming);

    //and finally, sweet release*/
    free( this->label );
    free( this );
}


Edge*
vLink(Vertex* this, Vertex* to, EdgePayload* payload) {
    //create edge object
    Edge* link = eNew(this, to, payload);

    ListNode* outlistnode = liNew( link );
    liInsertAfter( this->outgoing, outlistnode );
    this->degree_out++;

    ListNode* inlistnode = liNew( link );
    liInsertAfter( to->incoming, inlistnode );
    to->degree_in++;

    return link;
}

//the comments say it all
Edge*
vSetParent( Vertex* this, Vertex* parent, EdgePayload* payload ) {
    //delete all incoming edges
    ListNode* edges = vGetIncomingEdgeList( this );
    while(edges) {
      ListNode* nextnode = edges->next;
      eDestroy( edges->data, 0 );
      edges = nextnode;
    }

    //add incoming edge
    return vLink( parent, this, payload );
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
vRemoveOutEdgeRef( Vertex* this, Edge* todie ) {
    this->degree_out -= 1;
    liRemoveRef( this->outgoing, todie );
}

void
vRemoveInEdgeRef( Vertex* this, Edge* todie ) {
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

SPTVertex *
sptvNew( Vertex* mirror, int hop ) {
    SPTVertex *this = (SPTVertex *)malloc(sizeof(SPTVertex));
    
    vInit( (Vertex*)this, mirror->label );
    this->state = NULL;
    this->hop = hop;
    this->mirror = mirror;
    
    return this;
}

void
sptvDestroy(SPTVertex* this) {
    if( this->state ) {
        stateDestroy( this->state );
    }
    vDestroy( (Vertex*)this, 0 );
}

Edge*
sptvLink(SPTVertex* this, SPTVertex* to, EdgePayload* payload) {
    return vLink( (Vertex*)this, (Vertex*)to, payload );
}

Edge*
sptvSetParent( SPTVertex* this, SPTVertex* parent, EdgePayload* payload ) {
    return vSetParent( (Vertex*)this, (Vertex*)parent, payload );
}

inline ListNode*
sptvGetOutgoingEdgeList( SPTVertex* this ) {
    return vGetOutgoingEdgeList( (Vertex*)this );
}

inline ListNode*
sptvGetIncomingEdgeList( SPTVertex* this ) {
    return vGetIncomingEdgeList( (Vertex*)this );
}

void
sptvRemoveOutEdgeRef( SPTVertex* this, Edge* todie ) {
    vRemoveOutEdgeRef( (Vertex*)this, todie );
}

void
sptvRemoveInEdgeRef( SPTVertex* this, Edge* todie ) {
    vRemoveInEdgeRef( (Vertex*)this, todie );
}
    
char*
sptvGetLabel( SPTVertex* this ) {
    return vGetLabel( (Vertex*)this );
}

int
sptvDegreeOut( SPTVertex* this ) {
    return vDegreeOut( (Vertex*)this );
}

int
sptvDegreeIn( SPTVertex* this ) {
    return vDegreeIn( (Vertex*)this );
}

State*
sptvState( SPTVertex* this ) {
    return this->state;
}

int
sptvHop( SPTVertex* this ) {
    return this->hop;
}

Edge*
sptvGetParent( SPTVertex* this ) {
    ListNode* first_node = vGetIncomingEdgeList( (Vertex*)this );
    if( first_node )
        return first_node->data;
    else
        return NULL;
}

Vertex*
sptvMirror( SPTVertex* this ) {
    return this->mirror;
}

// EDGE FUNCTIONS

Edge*
eNew(Vertex* from, Vertex* to, EdgePayload* payload) {
    Edge *this = (Edge *)malloc(sizeof(Edge));
    this->from = from;
    this->to = to;
    this->payload = payload;
    this->enabled = 1;
    return this;
}

void
eDestroy(Edge *this, int destroy_payload) {
    //free payload
    if(destroy_payload)
      epDestroy( this->payload ); //destroy payload object and contents

    vRemoveOutEdgeRef( this->from, this );
    vRemoveInEdgeRef( this->to, this );
    free(this);
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

Vertex*
eGetFrom(Edge *this) {
  return this->from;
}

Vertex*
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
