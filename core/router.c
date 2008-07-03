#include <ruby.h>

Graph*
#ifndef RETRO
gShortestPathTree( Graph* this, char *from, char *to, State* init_state ) {
#else
gShortestPathTreeRetro( Graph* this, char *from, char *to, State* init_state ) {
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

  //Return Tree
//  rb_warn("creo nuevo grafo");
  Graph* spt = gNew();
  gAddVertex( spt, origin )->payload = init_state;
  //Priority Queue
//rb_warn("creo colas prioridades");
  dirfibheap_t q = dirfibheap_new( gSize( this ) );
  dirfibheap_insert_or_dec_key( q, gGetVertex( this, origin ), 0 );

/*
 *  CENTRAL ITERATION
 *
 */
//  rb_warn("inicio iteracion");
  while( !dirfibheap_empty( q ) ) {                  //Until the priority queue is empty:
    u = dirfibheap_extract_min( q );                 //get the lowest-weight Vertex 'u',

    if( !strcmp( u->label, target ) )                //(end search if reached destination vertex)
      break;

    spt_u = gGetVertex( spt, u->label );             //get corresponding SPT Vertex,
    du = (State*)spt_u->payload;                     //and get State of u 'du'.

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

      /*TODO: proposed edge evaluation procedure:
        (1) collapse edge using du
        (2) find node impedance from incoming collapsed edge to outgoing collapsed edge
        (3) new_dv = eWalk( collapsed_edge, nodeWalk( incoming, outgoing, node, du ) )
      */
 //rb_warn("Colapso");
#ifndef RETRO
      EdgePayload *collapsed = epCollapse( edge->payload, du );
      //EdgePayload* prev_collapsed = vParent( spt_u )->payload;
      //State *du_with_penalty = vWalk( spt_u, prev_collapsed, collapsed, du );
      //State *new_dv = epWalk( collapsed, du_with_penalty );
      State *new_dv = epWalk( collapsed, du );
#else
      EdgePayload *collapsed = epCollapseBack( edge->payload, du );
      State *new_dv = epWalkBack( collapsed, du );
#endif
   //    rb_warn("A1");
      // When an edge leads nowhere (as indicated by returning NULL), the iteration is over.
      if(!new_dv) {
        edges = edges->next;
        continue;
      }

      // States cannot have weights lower than their parent State.
      if(new_dv->weight < du->weight) {
        fprintf(stderr, "Negative weight (%s -> %s)(%ld) = %ld\n",edge->from->label, edge->to->label, du->weight, new_dv->weight);
        edges = edges->next;
        continue;
      }
  //     rb_warn("A5");
      long new_w = new_dv->weight;
      // If the new way of getting there is better,
      if( new_w < old_w ) {
 //       rb_warn("A51");
        dirfibheap_insert_or_dec_key( q, v, new_w );    // rekey v in the priority queue

        // If this is the first time v has been reached
//	rb_warn("A52");
        if( !spt_v ) {
          spt_v = gAddVertex( spt, v->label );        //Copy v over to the SPT
          count++;
          }

        if((count%10000) == 0)
          fprintf(stdout, "Shortest path tree size: %d\n",count);

        spt_v->payload = new_dv;                      //Set the State of v in the SPT to the current winner
//	rb_warn("A53");
        if(edge->geom!=NULL) vSetParentGeom( spt_v, spt_u, collapsed, edge->geom->data);
        else vSetParent( spt_v, spt_u, collapsed );      //Make u the parent of v in the SPT
      } else {
//	rb_warn("A5salida");
        free(new_dv); //new_dv will never be used; merge it with the infinite.
      }
//	rb_warn("A5next");
      edges = edges->next;
    }
  } // end while
 //  rb_warn("me piro");
  dirfibheap_delete( q );

  fprintf(stdout, "Final shortest path tree size: %d\n",count);
  return spt;
}
