#include <stdlib.h>
#include <assert.h>
#include "../graphserver.h"
#include "../graph.h"
#include "../heap.h"
#include "../contraction.h"
#include <string.h>

void test_empty_graph() {

  Graph *gg = gNew();
  WalkOptions *wo = woNew();

  CH *ch = get_contraction_hierarchies( gg, wo, 1 ); 

  assert( gSize( ch->up ) == 0 );
  assert( gSize( ch->down ) == 0 );

  woDestroy( wo );
  chDestroy( ch );
  gDestroy( gg );

}

void test_simple_graph() {
  
  // create a simple graph with two vertices and one edge
  Graph *gg = gNew();
  gAddVertex( gg, "A" );
  gAddVertex( gg, "B" );
  gAddEdge( gg, "A", "B", (EdgePayload*)streetNew( "AtoB", 10, 0 ) );

  // create a contraction hierarchy of the graph
  WalkOptions *wo = woNew();
  CH *ch = get_contraction_hierarchies( gg, wo, 1 );

  // asserts
  assert( gSize( ch->up ) == 2 );
  assert( gSize( ch->down ) == 2 );

  // clean up
  woDestroy( wo );
  chDestroy( ch );
  gDestroy( gg );
}

int main() {
  test_empty_graph();
  test_simple_graph();

  return 1;
}
