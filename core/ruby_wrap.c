#include "ruby.h"
#include "fibheap.h"
#include "dirfibheap.h"
#include "graph.h"
#include <sys/time.h>

//#define DEBUG 

//EDGETYPE CLASSES
VALUE cEdgePayload;
VALUE cLink;
VALUE cStreet;
VALUE cTripHopSchedule;
VALUE cTripHop;
//CORE MST CLASSES
VALUE cState;
//CORE GRAPH CLASSES
VALUE cVertex;
VALUE cEdge;
//STATE-TYPE CLASSES
VALUE cCalendar;
int count=0;
//UTILITY METHODS-------------------------------------------------------

inline Vertex* unpack_v( VALUE pack ) {
  Vertex* unpack_ptr;
  Data_Get_Struct(pack, Vertex, unpack_ptr);
  	#ifdef DEBUG 
	//	rb_warning("unpack vertex (R->C): %s",unpack_ptr->label);
  	#endif
  return unpack_ptr;
}

inline VALUE pack_v( Vertex* unpacked) {
  if(unpacked){
	#ifdef DEBUG 
   		//rb_warning("pack vertex (C->R): %s",unpacked->label);
	#endif
    	return Data_Wrap_Struct( cVertex, 0, 0, unpacked ); }
  else
    return Qnil;
}

//for returning references to vertices which should not delete
//the underlying C structure when garbage collected
inline VALUE pack_v_nice( Vertex* unpacked ) {
  if(unpacked){
	#ifdef DEBUG
    		//rb_warn("pack vertex nice (C->R): %s",unpacked->label);
	#endif
    return Data_Wrap_Struct( cVertex, 0, 0, unpacked );}
  else
    return Qnil;
}


inline Edge* unpack_e( VALUE pack ) {
  Edge* unpack_ptr;
  //rb_warn("unpack edge (R->C)");
  Data_Get_Struct(pack, Edge, unpack_ptr);
  return unpack_ptr;
}

//Ruby is not allowed to free an edge structure: that is the domain
//of the vertex that attaches to it
inline VALUE pack_e( Edge* unpacked) {
  if(unpacked){
    //rb_warn("pack edge (C->R)");
    return Data_Wrap_Struct(cEdge, 0, 0, unpacked);}
  else
    return Qnil;
}

inline CalendarDay* unpack_cal( VALUE packed ) {
  CalendarDay* unpacked_ptr;
  Data_Get_Struct( packed, CalendarDay, unpacked_ptr );
  return unpacked_ptr;
}

inline VALUE pack_cal( CalendarDay* unpacked ) {
  if( unpacked )
    return Data_Wrap_Struct( cCalendar, 0, 0, unpacked );
  else
    return Qnil;
}

inline Link* unpack_link( VALUE packed ) {
  Link* unpacked_ptr;
  Data_Get_Struct( packed, Link, unpacked_ptr );
  return unpacked_ptr;
}

inline VALUE pack_link( Link* unpacked ) {
  if( unpacked )
    return Data_Wrap_Struct( cLink, 0, 0, unpacked );
  else
    return Qnil;
}

inline Street* unpack_street( VALUE packed ) {
  Street* unpacked_ptr;
  Data_Get_Struct( packed, Street, unpacked_ptr );
  return unpacked_ptr;
}

inline VALUE pack_street( Street* unpacked ) {
  if( unpacked )
    return Data_Wrap_Struct( cStreet, 0, 0, unpacked );
  else
    return Qnil;
}

inline TripHopSchedule* unpack_ths( VALUE packed ) {
  TripHopSchedule* unpacked_ptr;
  Data_Get_Struct( packed, TripHopSchedule, unpacked_ptr );
  return unpacked_ptr;
}

inline VALUE pack_ths( TripHopSchedule* unpacked ) {
  if( unpacked )
    return Data_Wrap_Struct( cTripHopSchedule, 0, 0, unpacked );
  else
    return Qnil;
}

inline TripHop* unpack_triphop( VALUE packed ) {
  TripHop* unpacked_ptr;
  Data_Get_Struct( packed, TripHop, unpacked_ptr );
  return unpacked_ptr;
}

inline VALUE pack_triphop( TripHop* unpacked ) {
  if( unpacked )
    return Data_Wrap_Struct( cTripHop, 0, 0, unpacked );
  else
    return Qnil;
}

inline State* unpack_state( VALUE packed ) {
  State* unpacked_ptr;
  Data_Get_Struct( packed, State, unpacked_ptr );
  return unpacked_ptr;
}

inline VALUE pack_state( State* unpacked ) {
  if( unpacked )
    return Data_Wrap_Struct( cState, 0, 0, unpacked );
  else
    return Qnil;
}

VALUE pack_edge_type( edgepayload_t type ) {
  return INT2NUM( type );
}

inline EdgePayload* unpack_ep( VALUE rbpayload ) {
  EdgePayload* unpacked_ptr;
  Data_Get_Struct( rbpayload, EdgePayload, unpacked_ptr );
  return unpacked_ptr;
}

inline VALUE pack_ep_as_children( EdgePayload* unpacked ) {
  if(!unpacked)
    return Qnil;

  edgepayload_t type = unpacked->type;
  switch (type) {
    case PL_STREET:
      return pack_street( (Street*)unpacked );
    case PL_TRIPHOPSCHED:
      return pack_ths( (TripHopSchedule*)unpacked );
    case PL_TRIPHOP:
      return pack_triphop( (TripHop*)unpacked );
    case PL_LINK:
      return pack_link( (Link*)unpacked );
    case PL_RUBYVALUE:
      return (VALUE)unpacked;
    default:
      return Qnil;
  }
}

//EDGETYPE METHODS----------------------------------------------------

VALUE t_ep_collapse( VALUE self, VALUE rbstate ) {
  EdgePayload* ep = unpack_ep( self );
  State* state = unpack_state( rbstate );

  EdgePayload* ret = epCollapse( ep, state );

  return pack_ep_as_children( ret ); 
}

//LINK METHODS----------------------------------------------------------

VALUE t_link_new( VALUE class ) {
  return pack_link( linkNew() );
}

VALUE t_link_walk( VALUE self, VALUE rbstate ) {
  Link* li = unpack_link( self );
  State* state = unpack_state( rbstate );

  State* ret = linkWalk( li, state );

  return pack_state( ret );
}

VALUE t_link_walk_back( VALUE self, VALUE rbstate ) {
  Link* li = unpack_link( self );
  State* state = unpack_state( rbstate );

  State* ret = linkWalkBack( li, state );

  return pack_state( ret );
}

//STREET METHODS--------------------------------------------------------

VALUE t_street_new( VALUE class, VALUE rbname, VALUE rblength ) {
  char* name = STR2CSTR( rbname );
  double length = NUM2DBL( rblength );

  Street* ret = streetNew( name, length);

  return pack_street( ret );
}


VALUE t_street_name( VALUE self ) {
  return rb_str_new2( ((Street*)DATA_PTR( self ))->name );
}

VALUE t_street_length( VALUE self ) {
  return rb_float_new( ((Street*)DATA_PTR( self ))->length );
}

VALUE t_street_walk( VALUE self, VALUE rbstate ) {
  Street* str = unpack_street( self );
  State* state = unpack_state( rbstate );

  State* ret = streetWalk( str, state );

  return pack_state( ret );
}

VALUE t_street_walk_back( VALUE self, VALUE rbstate ) {
  Street* str = unpack_street( self );
  State* state = unpack_state( rbstate );

  State* ret = streetWalkBack( str, state );

  return pack_state( ret );
}

VALUE t_street_inspect( VALUE self ) {
  Street* street = unpack_street( self );
  char *ret;

  ret=(char *)malloc(sizeof(char)*512);
  sprintf( ret, "#<Street:%p name=\"%s\" length=%f>", street, street->name, street->length );

  return rb_str_new2( ret );
}

//TRIPHOPSCHEDULE METHODS----------------------------------------------------------

//rbtriphops is an array of [depart, arrive, trip_id]
VALUE t_ths_new( VALUE class, VALUE rbservice_id, VALUE rbtriphops, VALUE rbcalendar, VALUE rbtimezone_offset ) {
  long size = RARRAY(rbtriphops)->len;
  int* departs = (int*)malloc(size*sizeof(int));
  int* arrives = (int*)malloc(size*sizeof(int));
  char** trip_ids = (char**)malloc(size*sizeof(char*)+1);

  long i;
  for(i=0; i<size; i++) {
    VALUE triphop = rb_ary_entry(rbtriphops, i);

    departs[i] = NUM2INT(rb_ary_entry(triphop, 0));
    arrives[i] = NUM2INT(rb_ary_entry(triphop, 1));
    
    char* tid  = STR2CSTR( rb_ary_entry( triphop, 2 ) );
    int tid_len = strlen( tid ) + 1;
    trip_ids[i] = (char*)malloc(tid_len*sizeof(char)+1);
    memcpy( trip_ids[i], tid, tid_len );
  }
  int service_id = NUM2INT( rbservice_id );
  CalendarDay* calendar = unpack_cal( rbcalendar );
  int timezone_offset = NUM2INT( rbtimezone_offset );

  TripHopSchedule* raw = thsNew( departs, arrives, trip_ids, size, service_id, calendar, timezone_offset );

  free(departs);
  free(arrives);
  free(trip_ids);

  return pack_ths( raw );
}

VALUE t_ths_walk( VALUE self, VALUE rbstate ) {
  TripHopSchedule* ths = unpack_ths( self );
  State* state = unpack_state( rbstate );

  State* ret = thsWalk( ths, state );

  return pack_state( ret );
}

VALUE t_ths_walk_back( VALUE self, VALUE rbstate ) {
  TripHopSchedule* ths = unpack_ths( self );
  State* state = unpack_state( rbstate );

  State* ret = thsWalkBack( ths, state );

  return pack_state( ret );
}

VALUE t_ths_inspect( VALUE self ) {
  TripHopSchedule* ths = unpack_ths( self );

  char ret[512];
  sprintf( ret, "#<TripHopSchedule:%p service_id=%d n_trip_hops=%d>", ths, ths->service_id, ths->n );

  return rb_str_new2( ret );
}

VALUE t_ths_triphops( VALUE self ) {
  TripHopSchedule* ths = unpack_ths( self );

  VALUE ret = rb_ary_new();

  int i;
  for(i=0; i<ths->n; i++) {
    /*VALUE hop = rb_ary_new();
    rb_ary_push( hop, INT2NUM( ths->hops[i].depart ) );
    rb_ary_push( hop, INT2NUM( ths->hops[i].arrive ) );
    rb_ary_push( hop, INT2NUM( ths->hops[i].transit ) );
    rb_ary_push( hop, rb_str_new2( ths->hops[i].trip_id ) );*/

    rb_ary_push( ret, pack_triphop( &ths->hops[i] ) );
  }

  return ret;
}

VALUE t_ths_service_id( VALUE self ) {
  TripHopSchedule* ths = unpack_ths( self );

  return INT2NUM( ths->service_id );
}

//TRIPHOP METHODS-------------------------------------------------------
VALUE t_triphop_walk( VALUE self, VALUE rbstate ) {
  TripHop* th = unpack_triphop( self );
  State* state = unpack_state( rbstate );

  State* ret = triphopWalk( th, state );

  return pack_state( ret );
}

VALUE t_triphop_walk_back( VALUE self, VALUE rbstate ) {
  TripHop* th = unpack_triphop( self );
  State* state = unpack_state( rbstate );

  State* ret = triphopWalkBack( th, state );

  return pack_state( ret );
}


VALUE t_triphop_depart( VALUE self ) {
  TripHop* th = unpack_triphop( self );
  
  return INT2NUM( th->depart );
}

VALUE t_triphop_arrive( VALUE self ) {
  TripHop* th = unpack_triphop( self );

  return INT2NUM( th->arrive );
}

VALUE t_triphop_transit( VALUE self ) {
  TripHop* th = unpack_triphop( self );

  return INT2NUM( th->transit );
}

VALUE t_triphop_trip_id( VALUE self ) {
  TripHop* th = unpack_triphop( self );

  return rb_str_new2( th->trip_id );
}

//STATE CLASSES=========================================================
//CALENDAR METHODS------------------------------------------------------

VALUE t_cal_new( VALUE class ) {
  VALUE ret = Data_Wrap_Struct( cCalendar, 0, 0, NULL );
 
  rb_obj_call_init( ret, 0, 0 );
 
  return ret;
}

VALUE t_cal_append_day( VALUE self, VALUE begin_time, VALUE end_time, VALUE service_ids, VALUE daylight_savings ) {
  CalendarDay* this = unpack_cal( self );
  int n_service_ids = RARRAY( service_ids )->len;
  ServiceId* c_service_ids = (ServiceId*)malloc(n_service_ids*sizeof(ServiceId));

  int i;
  for(i=0; i<n_service_ids; i++) {
    c_service_ids[i] = NUM2INT( rb_ary_entry( service_ids, i ) );
  }

  CalendarDay*  ret = calAppendDay( this, NUM2LONG( begin_time ), NUM2LONG( end_time ), n_service_ids, c_service_ids, NUM2INT( daylight_savings ) );

  free( c_service_ids );

  DATA_PTR( self ) = ret;
  return self; 
}

VALUE t_cal_inspect( VALUE self ) {
  CalendarDay* this = unpack_cal( self );

  char ret[1024];
  if( this )
    sprintf( ret, "#<CalendarDay:%p begin_time=%ld end_time=%ld n_service_ids=%d>", this, this->begin_time, this->end_time, this->n_service_ids );
  else
    sprintf( ret, "#<CalendarDay:Empty>" );

  return rb_str_new2( ret );
}

VALUE t_cal_begin_time( VALUE self ) {
  CalendarDay* this = unpack_cal( self );
  
  return INT2NUM( this->begin_time );
}

VALUE t_cal_end_time( VALUE self ) {
  CalendarDay* this = unpack_cal( self );

  return INT2NUM( this->end_time );
}

VALUE t_cal_service_ids( VALUE self ) {
  CalendarDay* this = unpack_cal( self );

  VALUE ret = rb_ary_new();

  int i;
  for(i=0; i<this->n_service_ids; i++) {
    rb_ary_push( ret, INT2NUM( this->service_ids[i] ) );   
  }

  return ret;
}

VALUE t_cal_previous( VALUE self ) {
  CalendarDay* this = unpack_cal( self );

  CalendarDay* prev_day = this->prev_day;

  if(!prev_day)
    return Qnil;

  DATA_PTR( self ) = prev_day;
  return self; 
}

VALUE t_cal_next( VALUE self ) {
  CalendarDay* this = unpack_cal( self );

  CalendarDay* next_day = this->next_day;

  if(!next_day)
    return Qnil;

  DATA_PTR( self ) = next_day;
  return self;
}

VALUE t_cal_rewind( VALUE self ) {
  DATA_PTR( self ) = calRewind( DATA_PTR( self ) );
  return self;
}

VALUE t_cal_fast_forward( VALUE self ) {
  DATA_PTR( self ) = calFastForward( DATA_PTR( self ) );
  return self;
}

VALUE t_cal_day_of_or_after( VALUE self, VALUE rbtime ) {
  long time = NUM2LONG( rb_funcall( rbtime, rb_intern( "to_i" ), 0 ) );

  CalendarDay* ret = calDayOfOrAfter( DATA_PTR( self ), time );

  return pack_cal( ret );
}

VALUE t_cal_day_of_or_before( VALUE self, VALUE rbtime ) {
  long time = NUM2LONG( rb_funcall( rbtime, rb_intern( "to_i" ), 0 ) );

  CalendarDay* ret = calDayOfOrBefore( DATA_PTR( self ), time ) ;

  return pack_cal( ret );
}

//MST CORE OBJECTS======================================================
VALUE t_state_new( VALUE class, VALUE rbtime ) {
  long time = NUM2LONG( rb_funcall( rbtime, rb_intern( "to_i" ), 0 ) );

  VALUE ret = pack_state( stateNew( time ) );
 
  rb_obj_call_init( ret, 0, 0 );
 
  return ret;
}

VALUE t_state_set( VALUE self, VALUE rbkey, VALUE rbvalue ) {
  State* state = unpack_state( self );
  char* key = STR2CSTR( rb_funcall( rbkey, rb_intern( "to_s" ), 0 ) );

  if(!strcmp(key, "time"))
    state->time = NUM2LONG( rbvalue );
  else if (!strcmp(key, "weight"))
    state->weight = NUM2LONG( rbvalue );
  else if (!strcmp(key, "dist_walked"))
    state->dist_walked = NUM2DBL( rbvalue );
  else if (!strcmp(key, "num_transfers"))
    state->num_transfers = NUM2INT( rbvalue );
  else if (!strcmp(key, "prev_edge_type"))
    state->prev_edge_type = NUM2INT( rbvalue );
  else if (!strcmp(key, "prev_edge_name"))
    state->prev_edge_name = STR2CSTR( rbvalue );
  else if (!strcmp(key, "calendar_day"))
    state->calendar_day = unpack_cal( rbvalue );
  else
    return Qnil;

  return rbvalue;
}

VALUE t_state_to_hash( VALUE self ) {
  State* state = unpack_state( self );

  VALUE ret = rb_hash_new();
  rb_hash_aset( ret, rb_str_new2( "time" ), INT2NUM( state->time ) );
  rb_hash_aset( ret, rb_str_new2( "weight" ), INT2NUM( state->weight ) );
  rb_hash_aset( ret, rb_str_new2( "dist_walked" ), rb_float_new( state->dist_walked ) );
  rb_hash_aset( ret, rb_str_new2( "num_transfers" ), INT2NUM( state->num_transfers ) ) ;
  rb_hash_aset( ret, rb_str_new2( "prev_edge_type" ), INT2NUM( state->prev_edge_type ) );
  rb_hash_aset( ret, rb_str_new2( "prev_edge_name" ), (state->prev_edge_name?rb_str_new2(state->prev_edge_name ):Qnil ) );
  rb_hash_aset( ret, rb_str_new2( "calendar_day" ), pack_cal( state->calendar_day ) );

  return ret;
}

VALUE t_state_ref( VALUE self, VALUE rbkey ) {
  VALUE hsh = t_state_to_hash( self );
  return rb_hash_aref( hsh, rbkey );
}

VALUE t_state_inspect( VALUE self ) {
  VALUE hash = rb_funcall( self, rb_intern( "to_hash" ), 0 );

  return rb_inspect( hash );
}

VALUE t_state_dup( VALUE self ) {
  State* ret = stateDup( DATA_PTR( self ) );

  return pack_state( ret );
}

//GRAPH CORE OBJECTS====================================================
//VERTEX METHODS--------------------------------------------------------

VALUE t_v_each_incoming( VALUE self ) {
  Vertex* vv = unpack_v( self );
  ListNode* edges = vGetIncomingEdgeList( vv ); //head node is a dummy
  while(edges) {
    rb_yield( pack_e( edges->data ) );
    edges = edges->next;
  }

  return Qnil;
}

VALUE t_v_each_outgoing( VALUE self ) {
  Vertex* vv = unpack_v( self );
  ListNode* edges = vGetOutgoingEdgeList( vv ); //head node is a dummy
  while(edges) {
    rb_yield( pack_e( edges->data ) );
    edges = edges->next;
  }

  return Qnil;
}

static VALUE t_v_get_payload( VALUE self ) {
  Vertex* vv = unpack_v( self );

  return pack_state( vv->payload );
}

static VALUE t_v_degree_in( VALUE self ) {
  Vertex* vv = unpack_v( self );

  return INT2NUM( vv->degree_in );
}

static VALUE t_v_degree_out( VALUE self ) {
  Vertex* vv = unpack_v( self );

  return INT2NUM( vv->degree_out );
}

static VALUE t_v_label( VALUE self ) {
  Vertex* v = unpack_v( self );

  VALUE ret = rb_str_new2( v->label );

  return ret;
}

//EDGE METHODS-----------------------------------------------------------

static VALUE t_e_from( VALUE self ) {
  Edge* e = unpack_e( self );

  return pack_v_nice(e->from);
}

static VALUE t_e_to( VALUE self ) {
  Edge* e = unpack_e( self );

  return pack_v_nice(e->to);
}

static VALUE t_e_payload( VALUE self ) {
  Edge* e = unpack_e( self );

  return pack_ep_as_children( e->payload );
}


VALUE t_edge_geom( VALUE self ) {
  Edge* e = unpack_e( self );
  if (e->geom==NULL) return rb_str_new2("");
  return rb_str_new2(e->geom->data);
}

static VALUE t_e_walk( VALUE self, VALUE rbinit ) {
  Edge* e = unpack_e( self );

  State* init = unpack_state( rbinit );

  State* transformed = eWalk(e, init);

  return pack_state( transformed );
}

static VALUE t_e_inspect( VALUE self ) {
  char ret[1024];

  Edge* e = DATA_PTR( self );
  VALUE payload = rb_funcall( self, rb_intern( "payload" ), 0 );
  char* pl_str  = STR2CSTR( rb_funcall( payload, rb_intern( "inspect" ), 0 ) );

  sprintf(ret, "#<Edge:%p payload=%s>", e, pl_str );

  return rb_str_new2( ret );
}

//GRAPH METHODS----------------------------------------------------------

VALUE cGraph;

Graph* unpack_g( VALUE packed ) {
  Graph* unpacked_ptr;
  Data_Get_Struct(packed, Graph, unpacked_ptr);
  return unpacked_ptr;
}

VALUE pack_g( Graph* unpacked) {
  return Data_Wrap_Struct( cGraph, 0, 0, unpacked );
}

static void free_memory_graph(Graph * unpacked) {
 //libero la prueba
   rb_warn("clean graph route");
  gDestroy(unpacked,1,0);
}

VALUE pack_g_nice( Graph* unpacked) {
  //rb_warn("pack graph mio: C->R");
  return Data_Wrap_Struct( cGraph, 0, free_memory_graph, unpacked );
}
static VALUE t_init(VALUE self)
{
  Graph* ret = gNew();

  return pack_g( ret );
}

static VALUE t_add_vertex(VALUE self, VALUE key)
{
  Graph* gg = unpack_g( self );
  
  Vertex* vv = gAddVertex( gg, STR2CSTR( key ) );

  return pack_v( vv );
}

static VALUE t_get_vertex(VALUE self, VALUE key)
{
  Graph* gg = unpack_g( self );

  Vertex* vv = gGetVertex( gg, STR2CSTR( key ) );

  return pack_v( vv );
}

static VALUE t_add_edge(VALUE self, VALUE key_from, VALUE key_to, VALUE rbpayload)
{
  Graph* gg = unpack_g( self );

  Edge* ee = gAddEdge( gg, STR2CSTR( key_from ), STR2CSTR( key_to ), unpack_ep( rbpayload ) );

  return pack_e( ee );
}

static VALUE t_add_edge_geom(VALUE self, VALUE key_from, VALUE key_to, VALUE rbpayload, VALUE rbgeom)
{

  char *geom=STR2CSTR(rbgeom);
  Graph* gg = unpack_g( self );
  Edge* ee = gAddEdgeGeom( gg, STR2CSTR( key_from ), STR2CSTR( key_to ), unpack_ep( rbpayload ) ,geom);
  return pack_e( ee );
}

static VALUE t_vertices( VALUE self ) {
  Graph* gg = unpack_g( self );
  long nn;

  Vertex** all = gVertices( gg, &nn );

  VALUE ret = rb_ary_new();
  long i;
  for(i=0; i<nn; i++) {
    rb_ary_push( ret, pack_v( all[i] ) );
  }

  return ret;
}

static VALUE t_shortest_path_tree( VALUE self, VALUE from, VALUE to, VALUE init, VALUE direction ) {
  Graph* gg = unpack_g( self );
  count++; 
  Graph* tree;
  rb_warn("Quetioned route: %i",count);
  if( RTEST( direction ) ) {
    //allow for 'to' to be "nil" in order to create exhaustive SPT
    if( !RTEST( to ) )
      to = rb_str_new2( "" );
   // rb_warn("entro en la la llamada");
    tree = gShortestPathTree( gg, STR2CSTR( from ), STR2CSTR( to ), unpack_state( init ) );
    //rb_warn("tamaño: %i",gSize(tree));
  } else {
    //allows 'from' to be "nil" to create exhaustive SPT
    if( !RTEST( from ) )
      from = rb_str_new2( "" );
    //rb_warn("entro en la la llamada retro");
    tree = gShortestPathTreeRetro( gg, STR2CSTR( from ), STR2CSTR( to ), unpack_state( init ) );
    rb_warn("length route: %i",gSize(tree));
  }
  rb_warn("request complete number- %i - free memory",count); 
  return pack_g_nice( tree );

}

//For now it's a little easier to do this in Ruby
static VALUE t_shortest_path( VALUE self, VALUE from, VALUE to, VALUE init, VALUE direction ) {
  Graph* gg = unpack_g( self );

  long nn;
  State* path = gShortestPath( gg, STR2CSTR( from ), STR2CSTR( to ), unpack_state( init ), RTEST(direction), &nn );

  if( !path ) {
    return Qnil;
  }

  VALUE ret = rb_ary_new();
  int i;
  for(i=0; i<nn; i++) {
    rb_ary_push( ret, pack_state( &path[i] ) );
  }

  return ret;
}

void Init_graph_core() {

  //EDGETYPE OBJECTS
  cEdgePayload = rb_define_class( "EdgePayload", rb_cObject );
  rb_define_method( cEdgePayload, "collapse", t_ep_collapse, 1 );

  cLink = rb_define_class("Link", cEdgePayload);
  rb_define_singleton_method( cLink, "new", t_link_new, 0 );
  rb_define_method( cLink, "walk", t_link_walk, 1 );
  rb_define_method( cLink, "walk_back", t_link_walk_back, 1 );

  cStreet = rb_define_class("Street", cEdgePayload);
  rb_define_singleton_method( cStreet, "new", t_street_new, 2 );
  rb_define_method( cStreet, "name", t_street_name, 0 );
  rb_define_method( cStreet, "length", t_street_length, 0 );
  rb_define_method( cStreet, "walk", t_street_walk, 1 );
  rb_define_method( cStreet, "walk_back", t_street_walk_back, 1 );
  rb_define_method( cStreet, "inspect", t_street_inspect, 0 );


  cTripHopSchedule = rb_define_class("TripHopSchedule", cEdgePayload);
  rb_define_singleton_method( cTripHopSchedule, "new", t_ths_new, 4 );
  rb_define_method( cTripHopSchedule, "walk", t_ths_walk, 1 );
  rb_define_method( cTripHopSchedule, "walk_back", t_ths_walk_back, 1);
  rb_define_method( cTripHopSchedule, "inspect", t_ths_inspect, 0 );
  rb_define_method( cTripHopSchedule, "triphops", t_ths_triphops, 0 );
  rb_define_method( cTripHopSchedule, "service_id", t_ths_service_id, 0);
  
  cTripHop = rb_define_class( "TripHop", cEdgePayload) ;
  rb_define_method( cTripHop, "walk", t_triphop_walk, 1 );
  rb_define_method( cTripHop, "walk_back", t_triphop_walk_back, 1 );
  rb_define_method( cTripHop, "depart", t_triphop_depart, 0 );
  rb_define_method( cTripHop, "arrive", t_triphop_arrive, 0 );
  rb_define_method( cTripHop, "transit", t_triphop_transit, 0 );
  rb_define_method( cTripHop, "trip_id", t_triphop_trip_id, 0 );

  //STATE OBJECTS
  cCalendar = rb_define_class("Calendar", rb_cObject);
  rb_define_singleton_method( cCalendar, "new", t_cal_new, 0);
  rb_define_method( cCalendar, "append_day", t_cal_append_day, 4 );
  rb_define_method( cCalendar, "inspect", t_cal_inspect, 0 );
  rb_define_method( cCalendar, "begin_time", t_cal_begin_time, 0 );
  rb_define_method( cCalendar, "end_time", t_cal_end_time, 0 );
  rb_define_method( cCalendar, "service_ids", t_cal_service_ids, 0 );
  rb_define_method( cCalendar, "previous!", t_cal_previous, 0 );
  rb_define_method( cCalendar, "next!", t_cal_next, 0 );
  rb_define_method( cCalendar, "rewind!", t_cal_rewind, 0 );
  rb_define_method( cCalendar, "fast_forward!", t_cal_fast_forward, 0 );
  rb_define_method( cCalendar, "day_of_or_after", t_cal_day_of_or_after, 1 );
  rb_define_method( cCalendar, "day_of_or_before", t_cal_day_of_or_before, 1 );

  //MST CORE OBJECTS
  cState = rb_define_class( "State", rb_cObject );
  rb_define_singleton_method( cState, "new", t_state_new, 1 );
  rb_define_method( cState, "[]=", t_state_set, 2 );
  rb_define_method( cState, "[]", t_state_ref, 1 );
  rb_define_method( cState, "inspect", t_state_inspect, 0 );
  rb_define_method( cState, "to_hash", t_state_to_hash, 0 );
  rb_define_method( cState, "dup", t_state_dup, 0 );

  //GRAPH CORE OBJECTS
  cVertex = rb_define_class("Vertex", rb_cObject);
  rb_define_method(cVertex, "each_incoming", t_v_each_incoming, 0);
  rb_define_method(cVertex, "each_outgoing", t_v_each_outgoing, 0);
  rb_define_method(cVertex, "payload", t_v_get_payload, 0);
  rb_define_method(cVertex, "degree_in", t_v_degree_in, 0);
  rb_define_method(cVertex, "degree_out", t_v_degree_out, 0);
  rb_define_method(cVertex, "label", t_v_label, 0);

  cEdge = rb_define_class("Edge", rb_cObject);
  rb_define_method(cEdge, "to", t_e_to, 0);
  rb_define_method(cEdge, "from", t_e_from, 0);
  rb_define_method(cEdge, "payload", t_e_payload, 0);
  rb_define_method(cEdge, "geom", t_edge_geom, 0);
  rb_define_method(cEdge, "walk", t_e_walk, 1);
  rb_define_method(cEdge, "inspect", t_e_inspect, 0 );

  cGraph = rb_define_class("Graph", rb_cObject);
  rb_define_singleton_method( cGraph, "create", t_init, 0);
  rb_define_method(cGraph, "add_vertex", t_add_vertex, 1);
  rb_define_method(cGraph, "get_vertex", t_get_vertex, 1);
  rb_define_method(cGraph, "vertices", t_vertices, 0);
  rb_define_method(cGraph, "add_edge", t_add_edge, 3);
  rb_define_method(cGraph, "add_edge_geom", t_add_edge_geom, 4);
  rb_define_method(cGraph, "shortest_path_tree", t_shortest_path_tree, 4);
  rb_define_method(cGraph, "shortest_path", t_shortest_path, 4);
}
