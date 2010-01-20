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
    origin_v = gAddVertex( spt, origin );
    init_state->owner = origin_v;
    origin_v->payload = init_state;
    //Priority Queue
    fibheap_t q = fibheap_new();
    fibheap_insert( q, 0, init_state );
        
    // see if this adds much to execution time
    // this approach makes it faster 0.58 -> 0.48
    // as low as 0.05 difference, so not that important
    // gFreeStates( this );
    
    /*
     *  CENTRAL ITERATION
     *
     */
        
    while( !fibheap_empty( q ) ) {              //Until the priority queue is empty:
        du = fibheap_extract_min( q );
        du->queue_node = NULL;
        //    if( !strcmp( u->label, target ) )    //(end search if reached destination vertex)
        //      break;
        spt_u = du->owner; 
        /*
        if (strcmp(spt_u->label, target) == 0 && spt_u->bounding_state == NULL) {
            gDijkstraBounds( this, spt, to, du, options );
        }
         */
        u = gGetVertex( this, spt_u->label );
        // DEBUG
        // printf("got state. %s %ld\n", spt_u->label, du->time);

        // Abandon paths that exceed time limit.
        // Break is appropriate here because all subsequent states will have greater times.
        // We break out of the outer (queue) loop, not the inner (edge) loop.
#ifndef RETRO
        // DEBUG
        maxtime = init_state->time + 60 * 60 * 2;
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
        while( edges ) {                             //For each Edge 'edge' connecting u
            Edge* edge = edges->data;
            // DEBUG
            // printf("got edge. %s %s\n", edge->from->label, edge->to->label);

#ifndef RETRO
            v = edge->to;                            //to Vertex v:
#else
            v = edge->from;
#endif
            spt_v = gGetVertex( spt, v->label );     //get the SPT Vertex corresponding to 'v'
                                                     //might be null if it has not been copied!
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

            // Abandon paths that exceed some limits (optimization)
            // here we want to continue, not break, because it is possible to have later states with lower distance, etc.
            if( new_dv->dist_walked > options->max_walk || new_dv->num_transfers > options->max_transfers + 1 ) { // note difference between transfers and boardings
                // DEBUG
                // printf("excessive path length. abandoning.\n");
                stateDestroy(new_dv);
                edges = edges->next;
                continue;
            }
            
            if (spt_v) {
                // Abandon paths that arrive after time upper bounds
                /*
                if ( spt_v->bounding_state && spt_v->bounding_state->time < new_dv->time ) {
                    // DEBUG
                    // printf("pruning based on bounding state.\n");
                    edges = edges->next;
                    continue;
                }
                 */
                dv = spt_v->payload;
                State* prev_dv = NULL;
                while ( dv ) {
                    // DEBUG
                    // printf("Comp State: %ld %ld\n", dv->time, dv->weight);
                    
                    if (new_dv->weight >= dv->weight && new_dv->time >= dv->time) { // old is better in all respects
                    //if (new_dv->weight >= dv->weight && new_dv->time >= dv->time && new_dv->num_transfers >= dv->num_transfers && new_dv->dist_walked >= dv->dist_walked) { // new is better in all respects
                        // DEBUG
                        // printf("New state is worse. Abandoning.\n");
                        stateDestroy(new_dv); // new_dv will never be used; merge it with the infinite.
                        new_dv = NULL;        // signal that new state should not be added to the list
                        break;                // no need to keep searching - new state is worse than everything in the list.
                    }
                    // new state has already been discarded if it is equal in all respects to old.
                    // equality here ensures uniqueness of times and weights in a state list.
                    if (new_dv->weight <= dv->weight && new_dv->time <= dv->time) { // new is better in all respects
                    //if (new_dv->weight <= dv->weight && new_dv->time <= dv->time && new_dv->num_transfers <= dv->num_transfers && new_dv->dist_walked <= dv->dist_walked) { // new is better in all respects
                        // DEBUG
                        // printf("New state is better. Deleting old.\n");
                        // remove the old state from the linked list
                        if (prev_dv) { // old state is not the head
                            // DEBUG 
                            // printf("Old state is not head.\n");
                            prev_dv->next = dv->next;
                        } else { // old state is the head
                            // DEBUG
                            // printf("Old state is head.\n");
                            spt_v->payload = dv->next;
                        }
                        // DEBUG
                        // printf("Dequeueing.\n");
                        if (dv->queue_node) fibheap_delete_node(q, dv->queue_node); // dequeue the old state.
                        State* temp = dv;
                        // prev_dv = prev_dv; // noop: because current dv has been deleted
                        dv = dv->next;
                        // DEBUG
                        // printf("Destroying.\n");
                        stateDestroy(temp); // deallocate the old state
                    } else {
                        prev_dv = dv;
                        dv = dv->next;
                    }
                }
            }
            if (new_dv) { // check that we want to add the new state (that it has not been deleted)
                if( !spt_v ) { // If this is the first time v has been reached
                    spt_v = gAddVertex( spt, v->label ); // Copy v over to the SPT
                    count++;
                    // DEBUG
                    // printf("Added vertex to spt. %s\n", spt_v->label);
                }                            
                // DEBUG
                // printf("Keeping new state. Adding to linked list.\n");
                State* temp = spt_v->payload;
                spt_v->payload = new_dv;
                new_dv->next = temp;
                new_dv->owner = spt_v;
                new_dv->back_edge = edge;
                new_dv->back_state = du;
                new_dv->queue_node = fibheap_insert( q, new_dv->time, new_dv );    // put dv in the priority queue
            }
            /* DEBUG
            State* dv_disp = spt_v->payload;
            int dv_disp_n = 0;
            printf("NEW STATE LIST:\n");
            while (dv_disp) {
                printf("State: %ld %ld\n", dv_disp->time, dv_disp->weight);
                dv_disp = dv_disp->next;
                dv_disp_n++;
            }            
            printf("%d STATES.\n", dv_disp_n);
            */
            edges = edges->next;  // next edge from u to v
        }
    }
    
    fibheap_delete( q );
    
    /* DEBUG
    fprintf(stdout, "Final shortest path tree size: %d\n",count);
    v = gGetVertex(spt, target);
    if (v) {
        dv = v->payload;
        while (dv) {
            printf("Vertex: %s / ", dv->owner->label);
            printf("State: %f %ld\n", (dv->time - init_state->time) / 60.0, dv->weight);
            dv = dv->back_state;
        }        
    } else {
        printf("target was not reached.\n");
    }       
    */ 
    return spt;
}
    

#ifndef RETRO    
void
gDijkstraBounds( Graph* this, Graph* spt, char* to, State* init_state, WalkOptions* options ) { 
// it's not called retro, but it does a retro sub-search!     
// operate on an spt, not original graph. that way you don't have to init all the bounding state pointers.
// absence of a node could also indicate it's uselessness (i.e. visit time earlier than outer search's departure time.
#else    
void
gDijkstraBoundsRetro( Graph* this, Graph* spt, char* to, State* init_state, WalkOptions* options ) { // placeholder            
#endif
    
    printf("Dijkstra bounding.\n");
    
    /*
     *  VARIABLE SETUP
     */
    //Iteration Variables
    Vertex *u, *v, *origin_v;
    Vertex *spt_u, *spt_v;
    State *du, *dv;
    
    //Goal Variables
    //change for retro
    char* origin = to;
        
    //Return Tree
    origin_v = gGetVertex( spt, origin );
    origin_v->bounding_state = stateNew(init_state->n_agencies, init_state->weight); // yes, that's supposed to say weight
    origin_v->bounding_state->owner = origin_v; 
    
    //Priority Queue
    fibheap_t q = fibheap_new();
    fibheap_insert( q, 0, origin_v->bounding_state );
    
    /*
     *  CENTRAL ITERATION
     *
     */
    
    while( !fibheap_empty( q ) ) {                  //Until the priority queue is empty:
        du = fibheap_extract_min( q );
        du->queue_node = NULL;
        spt_u = du->owner;             
        u = gGetVertex( this, spt_u->label );
        //printf("at vertex %s time %ld.\n", spt_u->label, du->time); 
        
        //change for retro
        //if( du->time < mintime )
        //    break;
        
        //change for retro
        ListNode* edges = vGetIncomingEdgeList( u );

        while( edges ) {                                 //For each Edge 'edge' connecting u
            Edge* edge = edges->data;

            // change for retro
            v = edge->from;
            //printf("edge from %s.\n", v->label);
            long old_w;
            spt_v = gGetVertex( spt, v->label );
            if( spt_v ) {
                dv = (State*)spt_v->bounding_state; 
                if (dv) old_w = init_state->weight - dv->time;   // yes, that's supposed to say weight
                else old_w = INFINITY;
            } else {
                dv = NULL;                                       //which may not exist yet
                old_w = INFINITY;
            }
            
            // change for retro
            State *new_dv = eWalkBack( edge, du, options );
            
            // When an edge leads nowhere (as indicated by returning NULL), the iteration is over.
            if( !new_dv ) {
                edges = edges->next;
                continue;
            }
            
            long new_w = init_state->weight - new_dv->time; // yes, that's supposed to say weight
            // If the new way of getting there is better,
            //printf("new_w = %ld, old_w = %ld.\n", new_w, old_w);
            if( new_w < old_w ) {
                // If this is the first time v has been reached
                if( !spt_v ) {
                    spt_v = gAddVertex( spt, v->label );
                }
                if( dv ) {
                    if (dv->queue_node) {
                        new_dv->queue_node = dv->queue_node;
                        fibheap_replace_key_data ( q, dv->queue_node, new_w, new_dv);
                    } else {
                        new_dv->queue_node = fibheap_insert( q, new_w, new_dv );                
                    }
                    stateDestroy(dv);
                } else {
                    new_dv->queue_node = fibheap_insert( q, new_w, new_dv );                
                }
                spt_v->bounding_state = new_dv;                      //Set the State of v in the SPT to the current winner
                new_dv->owner=spt_v;
            } else {
                stateDestroy(new_dv); //new_dv will never be used; merge it with the infinite.
            }
            
            edges = edges->next;
        }
    }
    
    fibheap_delete( q );
}

