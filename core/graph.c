#include "graph.h"
#include "dirfibheap.h"

//GRAPH FUNCTIONS

Graph*
gNew() {
  Graph *this = (Graph*)malloc(sizeof(Graph));
  this->vertices = create_hashtable_string(16); //TODO: find a better number.

  return this;
}

void
gDestroy( Graph* this, int kill_vertex_payloads, int kill_edge_payloads ) {

  //destroy each vertex contained within
  struct hashtable_itr *itr = hashtable_iterator(this->vertices);
  int next_exists = hashtable_count(this->vertices);

  while(itr && next_exists) {
    Vertex* vtx = hashtable_iterator_value( itr );
    vDestroy( vtx, kill_vertex_payloads, kill_edge_payloads );
    next_exists = hashtable_iterator_advance( itr );
  }

  free(itr);
  //destroy the table
  hashtable_destroy( this->vertices, 0 );
  //destroy the graph object itself
  free( this );

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

Edge*
gAddEdgeGeom( Graph* this, char *from, char *to, EdgePayload *payload, char * datageom ) {
  Vertex* vtx_from = gGetVertex( this, from );
  Vertex* vtx_to   = gGetVertex( this, to );

  if(!(vtx_from && vtx_to))
    return NULL;

  return vLinkGeom( vtx_from, vtx_to, payload, datageom ); // link two vertices
}

Vertex**
gVertices( Graph* this, long* num_vertices ) {
  unsigned int nn = hashtable_count(this->vertices);
  Vertex** ret = (Vertex**)malloc(nn*sizeof(Vertex*));

  long i=0;
  struct hashtable_itr *itr = hashtable_iterator(this->vertices);
  int next_exists=1;

  while(itr && next_exists) {
    Vertex* vtx = hashtable_iterator_value( itr );
    ret[i] = vtx;
    next_exists = hashtable_iterator_advance( itr );
    i++;
  }

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
gShortestPath( Graph* this, char *from, char *to, State* init_state, int direction, long *size ) {
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
  Graph *raw_tree;
  Vertex *curr;
  if(direction) {
    raw_tree = gShortestPathTree( this, from, to, init_state );
    curr = gGetVertex( raw_tree, to );
  } else {
    raw_tree = gShortestPathTreeRetro( this, from, to, init_state );
    curr = gGetVertex( raw_tree, from );
  }

  if( !curr ) {
    gDestroy(raw_tree, 1, 0); //destroy raw_table and contents, as they won't be used
    fprintf( stderr, "Destination vertex never reached\n" );
    return NULL;
  }

  //TODO: replace ret with a resizeable array
  State *temppath = (State*)malloc(LARGEST_ROUTE_SIZE*sizeof(State));


  int i=0;
  while( curr ) {
    if( i > LARGEST_ROUTE_SIZE ) {         //Bail if our crude memory management techniques fail
      gDestroy( raw_tree, 1, 0 );
      free(temppath);
      fprintf( stderr, "Route %d hops long, larger than preallocated %d hops\n", i, LARGEST_ROUTE_SIZE );
      return NULL;
    }

    temppath[i] = *((State*)(curr->payload));
    i++;

    if( curr->degree_in == 0 )
      break;
    else
      curr = vGetIncomingEdgeList( curr )->data->from;
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


long
gSize( Graph* this ) {
  return hashtable_count( this->vertices );
}


// VERTEX FUNCTIONS

Vertex *
vNew( char* label ) {
    Vertex *this = (Vertex *)malloc(sizeof(Vertex)) ;
    this->degree_in = 0;
    this->degree_out = 0;
    this->outgoing = liNew( NULL ) ;
    this->incoming = liNew( NULL ) ;
    this->payload = NULL;

    size_t labelsize = strlen(label)+1;
    this->label = (char*)malloc(labelsize*sizeof(char));
    strcpy(this->label, label);

    return this ;
}

void
vDestroy(Vertex *this, int free_vertex_payload, int free_edge_payloads) {
    if( free_vertex_payload && this->payload )
      stateDestroy( this->payload );

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

Edge*
vLinkGeom(Vertex* this, Vertex* to, EdgePayload* payload, char* datageom) {
    // create edge object
    Edge* link = eNewGeom(this, to, payload, datageom);

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

Edge*
vSetParentGeom( Vertex* this, Vertex* parent, EdgePayload* payload, char * geomdata ) {
    //delete all incoming edges
    ListNode* edges = vGetIncomingEdgeList( this );
    while(edges) {
      eDestroy( edges->data, 0 );
      edges = edges->next;
    }

    //add incoming edge
    return vLinkGeom( parent, this, payload, geomdata);
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
    liRemoveRef( this->outgoing, todie );
}

void
vRemoveInEdgeRef( Vertex* this, Edge* todie ) {
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

State*
vPayload( Vertex* this ) {
	return this->payload;
}

// EDGE FUNCTIONS

Edge*
eNew(Vertex* from, Vertex* to, EdgePayload* payload) {
    Edge *this = (Edge *)malloc(sizeof(Edge));
    this->from = from;
    this->to = to;
    this->payload = payload;
    this->geom = NULL;
    return this;
}

Edge*
eNewGeom(Vertex* from, Vertex* to, EdgePayload* payload,char * datageom) {
    Edge *this = (Edge *)malloc(sizeof(Edge));
    this->from = from;
    this->to = to;
    this->payload = payload;
    this->geom = geomNew(datageom);
    return this;
}

void
eDestroy(Edge *this, int destroy_payload) {
    //free payload
    if(destroy_payload)
      epDestroy( this->payload ); //destroy payload object and contents

    vRemoveOutEdgeRef( this->from, this );
    vRemoveInEdgeRef( this->to, this );
    geomDestroy(this->geom);
    free(this);
}

State*
eWalk(Edge *this, State* params) {
  return epWalk( this->payload, params );
}

State*
eWalkBack(Edge *this, State* params) {
  return epWalkBack( this->payload, params );
}

Edge*
eGeom(Edge* this,char * datageom) {
	this->geom = geomNew(datageom);
	return this;
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

// LIST FUNCTIONS

ListNode*
liNew(Edge *data) {
    ListNode *ret = (ListNode*)malloc(sizeof(ListNode));
    ret->data = data;
    ret->next = NULL;
    return ret;
}

void
liInsertAfter( ListNode *this, ListNode* add ) {
    add->next = this->next;
    this->next = add;
}

void
liRemoveAfter( ListNode *this ) {
    if( this->next ) {
      ListNode* condemned = this->next;
      this->next = this->next->next;
      free( condemned );
    }
}

void
liRemoveRef( ListNode *dummyhead, Edge *data ) {
    ListNode* prev = dummyhead;
    ListNode* curr = dummyhead->next;

    while(curr) {
      if(curr->data == data) {
        liRemoveAfter( prev );
        break;
      }
      prev = curr;
      curr = prev->next;
    }
}

Edge*
liGetData( ListNode *this ) {
	return this->data;
}

ListNode*
liGetNext( ListNode *this ) {
	return this->next;
}

