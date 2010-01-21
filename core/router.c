#ifdef DEBUG
#define LOG(...) printf(__VA_ARGS__);
#else
#define LOG(...) // printf(__VA_ARGS__);
#endif 

Graph*
#ifndef RETRO
gShortestPathTree( Graph* this, char *from, char *to, State* init_state, WalkOptions* options, long maxtime ) {
    maxtime = init_state->time + 60 * 60 * 2;  // TESTING
#else
gShortestPathTreeRetro( Graph* this, char *from, char *to, State* init_state, WalkOptions* options, long mintime ) {
    mintime = init_state->time - 60 * 60 * 2;  // TESTING
#endif
        
    /*
     *  VARIABLE SETUP
     */
    
    //Iteration Variables
    Vertex *u, *v;
    Vertex *spt_u, *spt_v;
    State *du, *dv;
    
    //Goal Variables
#ifndef RETRO
    char* origin = from;
    char* target = to;
#else
    char* origin = to;
    char* target = from;
#endif
    
    // Get the origin vertex to make sure it exists
    Vertex* origin_v = gGetVertex( this, origin );
    if( origin_v == NULL ) return NULL;
    
    // Return Tree
    Graph* spt = gNew();
    origin_v = gAddVertex( spt, origin );
    init_state->owner = origin_v;
    origin_v->payload = init_state;
    
    // Priority Queue
    fibheap_t q = fibheap_new();
    fibheap_insert( q, 0, init_state );
        
    /*
     *  CENTRAL ITERATION
     *
     */
        
    while( !fibheap_empty( q ) ) {                    // Until the priority queue is empty:
        du = fibheap_extract_min( q );                // Get the next state in the queue (du).
        du->queue_node = NULL;                        // Signal that du is no longer in the queue.
        spt_u = du->owner;                            // Find out which vertex (u) this state belongs to.
        u = gGetVertex( this, spt_u->label );         // Get the corresponding vertex in the original graph.
        LOG("got state. %s %ld\n", spt_u->label, du->time);
#ifndef RETRO
        if( du->time > maxtime ) break;               // Terminate if all subsequent states will have excessive times.
        ListNode* edges = vGetOutgoingEdgeList( u );  // Otherwise get the head of vertex v's edge list.
#else
        if( du->time < mintime ) break;
        ListNode* edges = vGetIncomingEdgeList( u );
#endif
        while( edges ) {  
            Edge* edge = edges->data;                    // For each Edge out of u:
            LOG("got edge. %s %s\n", edge->from->label, edge->to->label);
#ifndef RETRO
            v = edge->to;                                // Get the edge's destination (v),
            State *new_dv = eWalk( edge, du, options );  // And the new state after traversing the edge.
#else
            v = edge->from;
            State *new_dv = eWalkBack( edge, du, options );
#endif
            if(!new_dv) {             // When an edge leads nowhere (as indicated by NULL),
                edges = edges->next;  // Move on to the next one.
                continue;
            }
            if(new_dv->weight < du->weight) {  // States cannot have weights lower than their parent State.
                fprintf(stderr, "Negative weight (%s(%ld) -> %s(%ld))\n",edge->from->label, du->weight, edge->to->label, new_dv->weight);
                edges = edges->next;
                continue;
            }
            // Abandon paths that exceed some limits.
            if( new_dv->dist_walked > options->max_walk || new_dv->num_transfers > options->max_transfers + 1 ) {
                LOG("excessive path length. abandoning.\n");
                stateDestroy(new_dv);          // Don't leave the new state (which will not be used) lying around.
                edges = edges->next;
                continue;                      // Continue (not break) because later states can have lower distance, etc.
            }
            spt_v = gGetVertex(spt, v->label); // Get the SPT Vertex corresponding to v (or NULL if it has not been reached).
            if (spt_v) {                       // If the vertex v is already present in the spt,
                dv = spt_v->payload;           // get the head of its state list,
                State* prev_dv = NULL;         // and keep track of the previous list element for deletions.
                while ( dv ) {                 // While there is another state to be examined :
                    LOG("Comp State: %ld %ld\n", dv->time, dv->weight);                    
                    // If the existing state is better than or equal to the new one in all respects :
                    if (new_dv->weight >= dv->weight && new_dv->time >= dv->time) { 
                        LOG("New state is worse. Abandoning.\n");
                        stateDestroy(new_dv);  // new_dv will never be used; merge it with the infinite.
                        new_dv = NULL;         // Signal that the new state should not be added to the list.
                        break;                 // No need to keep searching; the new state is dominated.
                    }
                    // At this point, the new state has already been discarded if it is equal in all respects to old.
                    // Equality below ensures the uniqueness of times and weights within a state list.
                    // If the existing state is worse than or equal to the new one in all respects :
                    if (new_dv->weight <= dv->weight && new_dv->time <= dv->time) {
                        // Remove the old state from the linked list
                        LOG("New state is better. Removing old. ");
                        if (prev_dv) prev_dv->next = dv->next; // Current existing state is not the list head.
                        else spt_v->payload = dv->next;        // Current existing state is the list head.
                        LOG("Dequeueing. ");
                        if (dv->queue_node) fibheap_delete_node(q, dv->queue_node); // dequeue the old state.
                        State* temp = dv;
                        // No need to update prev_dv because current dv has been deleted.
                        dv = dv->next;
                        LOG("Destroying. \n");
                        stateDestroy(temp); // deallocate the old state
                    } else {  // The new state is not dominated, and does not dominate the current existing state.
                        prev_dv = dv;   // Must keep a reference to the current state in case of deletions.
                        dv = dv->next;  // On to the next state.
                    }
                }  // Next state in the list...
            }
            if (new_dv) {  // Check that after examining the list of states, we have decided to add the new state.
                if( !spt_v ) {  // If this is the first time v has been reached:
                    spt_v = gAddVertex( spt, v->label );  // Copy v over to the SPT.
                    LOG("Added vertex to spt. %s\n", spt_v->label);
                }                            
                LOG("Keeping new state. Adding to linked list.\n");
                State* temp = spt_v->payload;   // Grab the old list head.
                spt_v->payload = new_dv;        // Insert the new state as the list head.
                new_dv->next = temp;            // Attach the old list after the new one.
                new_dv->owner = spt_v;          // Tell the new state which SPT vertex it belongs to.
                new_dv->back_edge = edge;       // Record how we got here for reporting paths later.
                new_dv->back_state = du;        // Ditto.
                new_dv->queue_node = fibheap_insert( q, new_dv->time, new_dv );  // Put new state in the priority queue
            }
#ifdef DEBUG
            // Print out a list of states at each visit to a vertex.
            State* dv_disp = spt_v->payload;
            int dv_disp_n = 0;
            printf("NEW STATE LIST:\n");
            while (dv_disp) {
                printf("State: %ld %ld\n", dv_disp->time, dv_disp->weight);
                dv_disp = dv_disp->next;
                dv_disp_n++;
            }            
            printf("%d STATES.\n", dv_disp_n);
#endif
            edges = edges->next;  
        }                 // Next edge from u to v...
    }                     // Next state from the queue...
    fibheap_delete( q );  // Free the priority queue.    
    return spt;           // Done! 
}