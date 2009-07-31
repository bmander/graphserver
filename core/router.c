Graph*
#ifndef RETRO
gShortestPathTree( Graph* this, char *from, char *to, State* init_state, WalkOptions* options, long maxtime ) {
#else
gShortestPathTreeRetro( Graph* this, char *from, char *to, State* init_state, WalkOptions* options, long mintime ) {
#endif
    
/*
 *  VARIABLE SETUP
 */
  //Iteration Variables
  Vertex *u, *v;
  Vertex *spt_u, *spt_v;
  State *du, *dv;
  int count = 1;

  //Goal Variables
#ifndef RETRO
  char* origin = from;
  char* target = to;
#else
  char* origin = to;
  char* target = from;
#endif

  //Get origin vertex to make sure it exists
  Vertex* origin_v = gGetVertex( this, origin );
  if( origin_v == NULL ) {
    return NULL;
  }
    
  //Return Tree
  Graph* spt = gNew();
  gAddVertex( spt, origin )->payload = init_state;
  //Priority Queue
  dirfibheap_t q = dirfibheap_new( gSize( this ) );
  dirfibheap_insert_or_dec_key( q, gGetVertex( this, origin ), 0 );

/*
 *  CENTRAL ITERATION
 *
 */

  while( !dirfibheap_empty( q ) ) {                  //Until the priority queue is empty:
    u = dirfibheap_extract_min( q );                 //get the lowest-weight Vertex 'u',

    if( !strcmp( u->label, target ) )                //(end search if reached destination vertex)
      break;

    spt_u = gGetVertex( spt, u->label );             //get corresponding SPT Vertex,
    
    du = (State*)spt_u->payload;                     //and get State of u 'du'.
    
#ifndef RETRO
    if( du->time > maxtime )
      break;
#else
    if( du->time < mintime )
      break;
#endif

#ifndef RETRO
    ListNode* edges = vGetOutgoingEdgeList( u );
#else
    ListNode* edges = vGetIncomingEdgeList( u );
#endif
    while( edges ) {                                 //For each Edge 'edge' connecting u
      Edge* edge = edges->data;
#ifndef RETRO
      v = edge->to;                                  //to Vertex v:
#else
      v = edge->from;
#endif

      long old_w;
      if( (spt_v = gGetVertex( spt, v->label )) ) {        //get the SPT Vertex corresponding to 'v'
        dv = (State*)spt_v->payload;                     //and its State 'dv'
        old_w = dv->weight;
      } else {
        dv = NULL;                                       //which may not exist yet
        old_w = INFINITY;
      }

#ifndef RETRO
      State *new_dv = eWalk( edge, du, options );
#else
      State *new_dv = eWalkBack( edge, du, options );
#endif

      // When an edge leads nowhere (as indicated by returning NULL), the iteration is over.
      if(!new_dv) {
        edges = edges->next;
        continue;
      }

      // States cannot have weights lower than their parent State.
      if(new_dv->weight < du->weight) {
        fprintf(stderr, "Negative weight (%s(%ld) -> %s(%ld))\n",edge->from->label, du->weight, edge->to->label, new_dv->weight);
        edges = edges->next;
        continue;
      }

      long new_w = new_dv->weight;
      // If the new way of getting there is better,
      if( new_w < old_w ) {
        dirfibheap_insert_or_dec_key( q, v, new_w );    // rekey v in the priority queue

        // If this is the first time v has been reached
        if( !spt_v ) {
          spt_v = gAddVertex( spt, v->label );        //Copy v over to the SPT
          count++;
          }

        //if((count%10000) == 0)
        //  fprintf(stdout, "Shortest path tree size: %d\n",count);

        if(spt_v->payload)
            stateDestroy(spt_v->payload);
        spt_v->payload = new_dv;                      //Set the State of v in the SPT to the current winner

        vSetParent( spt_v, spt_u, edge->payload );      //Make u the parent of v in the SPT
      } else {
        stateDestroy(new_dv); //new_dv will never be used; merge it with the infinite.
      }
      edges = edges->next;
    }
  }

  dirfibheap_delete( q );

  //fprintf(stdout, "Final shortest path tree size: %d\n",count);
  return spt;
}
