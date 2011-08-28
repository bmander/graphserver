ShortestPathTree*
#ifndef RETRO
gShortestPathTree( Graph* this, char *from, char *to, State* init_state, WalkOptions* options, long maxtime, int hoplimit, long weightlimit ) {
#else
gShortestPathTreeRetro( Graph* this, char *from, char *to, State* init_state, WalkOptions* options, long mintime, int hoplimit, long weightlimit ) {
#endif
    
/*
 *  VARIABLE SETUP
 */

  // iteration Variables
  Vertex *u, *v;
  SPTVertex *spt_u, *spt_v;
  State *du, *dv;
  int count = 1;

  // goal Variables
#ifndef RETRO
  char* origin = from;
  char* target = to;
#else
  char* origin = to;
  char* target = from;
#endif

  // get origin vertex to make sure it exists
  Vertex* origin_v = gGetVertex( this, origin );
  if( origin_v == NULL ) {
    return NULL;
  }
    
  // return Tree
  ShortestPathTree* spt = sptNew();
  spt_u = sptAddVertex( spt, origin_v, 0 );
  spt_u->state = init_state;
  spt_u->mirror = origin_v;
  // priority Queue
  fibheap_t q = fibheap_new();
  spt_u->fibnode = fibheap_insert( q, 0, (void*)spt_u );

/*
 *  CENTRAL ITERATION
 *
 */


  // until the priority queue is empty:
  while( !fibheap_empty( q ) ) {

    // get the closest vertex not yet reached
    spt_u = (SPTVertex*)fibheap_extract_min( q );
    u = spt_u->mirror;

    // end search if reached destination vertex
    if( !strcmp( u->label, target ) ) {
      break;
    }

    if( spt_u->hop >= hoplimit ) {
      break;
    }
    
    if( spt_u->state->weight > weightlimit ) {
      break;
    }

    du = (State*)spt_u->state;                     
    
#ifndef RETRO
    if( du->time > maxtime ) {
      break;
    }
#else
    if( du->time < mintime ) {
      break;
    }
#endif

#ifndef RETRO
    ListNode* edges = vGetOutgoingEdgeList( u );
#else
    ListNode* edges = vGetIncomingEdgeList( u );
#endif
    // for each u -- edge --> v 
    while( edges ) {                                 
      Edge* edge = edges->data;
#ifndef RETRO
      v = gGetVertexByIndex( this, edge->to );
#else
      v = gGetVertexByIndex( this, edge->from );
#endif

      long old_w;

      spt_v = sptGetVertex( spt, v->label );

      // get the SPT Vertex corresponding to 'v'
      if( spt_v ) {        
        // and its State 'dv'
        dv = (State*)spt_v->state;
        old_w = dv->weight;
      } else {
        // which may not exist yet
        dv = NULL;                      
        old_w = INFINITY;
      }

#ifndef RETRO
      State *new_dv = eWalk( edge, du, options );
#else
      State *new_dv = eWalkBack( edge, du, options );
#endif

      // when an edge leads nowhere (as indicated by returning NULL), the iteration is over.
      if(!new_dv) {
        edges = edges->next;
        continue;
      }

      // states cannot have weights lower than their parent State.
      if(new_dv->weight < du->weight) {
        fprintf(stderr, "Negative weight (%s(%ld) -> %s(%ld))\n",gGetVertexByIndex( this, edge->from )->label, du->weight, gGetVertexByIndex( this, edge->to )->label, new_dv->weight);
        edges = edges->next;
	stateDestroy( new_dv );
        continue;
      }

      long new_w = new_dv->weight;

      // if the new way of getting there is better,
      if( new_w < old_w ) {

        // if this is the first time v has been reached
        if( !spt_v ) {
          // copy v over to the SPT
          spt_v = sptAddVertex( spt, v, spt_u->hop+1 );        

          spt_v->fibnode = fibheap_insert( q, new_w, (void*)spt_v );
          count++;
        } else {
          fibheap_replace_key( q, spt_v->fibnode, new_w );
        }

        if(spt_v->state) {
          stateDestroy(spt_v->state);
        }

        // set the State of v in the SPT to the current winner
        spt_v->state = new_dv;                      

        // make u the parent of v in the SPT
        sptvSetParent( spt_v, spt_u, edge->payload );      
      } else {
        // new_dv will never be used; merge it with the infinite.
        stateDestroy(new_dv); 
      }
      edges = edges->next;
    }
  }

  fibheap_delete( q );

  return spt;
}
