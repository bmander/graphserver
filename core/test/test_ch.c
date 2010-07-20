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

int main() {
  test_empty_graph();

  return 1;
}
