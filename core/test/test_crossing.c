#include <stdlib.h>
#include <assert.h>
#include "../graphserver.h"
#include <string.h>

void test_create_destroy() {
  // create a blank crossing
  Crossing *cr = crNew();

  // check that it contains default values
  assert( cr->type == PL_CROSSING );
  assert( cr->n == 0 );
  assert( cr->crossing_times == NULL );
  assert( cr->crossing_time_trip_ids == NULL );

  // destroy it
  crDestroy( cr );
}

void test_add_single_crossing_time() {
  int CRTIME1 = 10;

  // create a blank crossing
  Crossing *cr = crNew();

  // add a single crossing time
  crAddCrossingTime(cr, "A", CRTIME1 );

  // get the crossing time by trip id
  assert( crGetCrossingTime( cr, "A" ) == CRTIME1 );

  // get crossing id and time by crossing index
  assert( strcmp( crGetCrossingTimeTripIdByIndex( cr, 0 ), "A" )==0 ); 
  assert( crGetCrossingTimeByIndex( cr, 0 ) == CRTIME1 );

  // check the crossing list is the right length
  assert( crGetSize(cr) == 1 );

  // destroy it
  crDestroy( cr );

}

void test_add_two_crossing_times() {
  int CRTIME1 = 10;
  int CRTIME2 = 20;

  // create a blank crossing
  Crossing *cr = crNew();

  // add a single crossing time
  crAddCrossingTime(cr, "A", CRTIME1 );
  crAddCrossingTime(cr, "B", CRTIME2 );

  // get the crossing time by trip id
  assert( crGetCrossingTime( cr, "A" ) == CRTIME1 );
  assert( crGetCrossingTime( cr, "B" ) == CRTIME2 );

  // get crossing id and time by crossing index
  assert( strcmp( crGetCrossingTimeTripIdByIndex( cr, 0 ), "A" )==0 ); 
  assert( crGetCrossingTimeByIndex( cr, 0 ) == CRTIME1 );
  assert( strcmp( crGetCrossingTimeTripIdByIndex( cr, 1 ), "B" )==0 ); 
  assert( crGetCrossingTimeByIndex( cr, 1 ) == CRTIME2 );

  // check the crossing list is the right length
  assert( crGetSize(cr) == 2 );

  // destroy it
  crDestroy( cr );

}

void test_add_several_crossing_times() {
  int CRTIME1 = 10;
  int CRTIME2 = 20;
  int CRTIME3 = 30;

  // create a blank crossing
  Crossing *cr = crNew();

  // add a single crossing time
  crAddCrossingTime(cr, "A", CRTIME1 );
  crAddCrossingTime(cr, "B", CRTIME2 );
  crAddCrossingTime(cr, "C", CRTIME3 );

  // get the crossing time by trip id
  assert( crGetCrossingTime( cr, "A" ) == CRTIME1 );
  assert( crGetCrossingTime( cr, "B" ) == CRTIME2 );
  assert( crGetCrossingTime( cr, "C" ) == CRTIME3 );

  // get crossing id and time by crossing index
  assert( strcmp( crGetCrossingTimeTripIdByIndex( cr, 0 ), "A" )==0 ); 
  assert( crGetCrossingTimeByIndex( cr, 0 ) == CRTIME1 );
  assert( strcmp( crGetCrossingTimeTripIdByIndex( cr, 1 ), "B" )==0 ); 
  assert( crGetCrossingTimeByIndex( cr, 1 ) == CRTIME2 );
  assert( strcmp( crGetCrossingTimeTripIdByIndex( cr, 2 ), "C" )==0 ); 
  assert( crGetCrossingTimeByIndex( cr, 2 ) == CRTIME3 );

  // check the crossing list is the right length
  assert( crGetSize(cr) == 3 );

  // destroy it
  crDestroy( cr );

}

void test_trip_doesnt_exist() {
  // create a crossing
  Crossing *cr = crNew();

  // try to get a trip that doesn't exist
  assert( crGetCrossingTime( cr, "A" ) == -1 );

  // destroy the crossing
  crDestroy( cr );
}

void test_index_out_of_bounds() {
  // create a crossing
  Crossing *cr = crNew();

  // get indexes out of bounds
  assert( crGetCrossingTimeTripIdByIndex( cr, -1 ) == NULL );
  assert( crGetCrossingTimeTripIdByIndex( cr, 0 ) == NULL );
  assert( crGetCrossingTimeTripIdByIndex( cr, 1 ) == NULL );
  assert( crGetCrossingTimeByIndex( cr, -1 ) == -1 );
  assert( crGetCrossingTimeByIndex( cr, 0 ) == -1 );
  assert( crGetCrossingTimeByIndex( cr, 1 ) == -1 );

  // add a single crossing
  crAddCrossingTime( cr, "A", 10 );

  // get indexes out of bounds
  assert( crGetCrossingTimeTripIdByIndex( cr, -1 ) == NULL );
  assert( crGetCrossingTimeTripIdByIndex( cr, 0 ) != NULL );
  assert( crGetCrossingTimeTripIdByIndex( cr, 1 ) == NULL );
  assert( crGetCrossingTimeByIndex( cr, -1 ) == -1 );
  assert( crGetCrossingTimeByIndex( cr, 0 ) != -1 );
  assert( crGetCrossingTimeByIndex( cr, 1 ) == -1 );

  // destroy crossing
  crDestroy( cr );
}

int main() {

  test_create_destroy();
  test_add_single_crossing_time();
  test_add_two_crossing_times();
  test_add_several_crossing_times();
  test_trip_doesnt_exist();
  test_index_out_of_bounds();

  return 1;
}
