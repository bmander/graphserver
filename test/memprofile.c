#include "stdio.h"
#include "../../graph.h"
#include <valgrind/callgrind.h>

int main() {
  CALLGRIND_STOP_INSTRUMENTATION;
  printf("reading streets.out\n");
  FILE* fp = fopen( "streets.out", "r" );
  Graph* gg = gNew();

  char from[20];
  char to[20];
  char via[20];
  double length;
  while( !feof( fp ) ) {
    fscanf(fp, "%s %s %s %lf\n", &from, &to, &via, &length);
    gAddVertex( gg, from, NULL );
    gAddVertex( gg, to, NULL );
    gAddStreet( gg, from, to, via, length );
    gAddStreet( gg, to, from, via, length );
  }
  fclose( fp );

  printf("reading busses.out\n");
  int ct=0;
  fp = fopen( "busses.out", "r" );
  int n;
  while( !feof( fp ) ) {
    if( ct%50 == 0 )
      printf("%d\n", ct);

    fscanf(fp, "%s %s %d\n", &from, &to, &n);

    int departs[n];
    int arrives[n];
    char* trip_ids[n];
    int* daymasks[n];

    int i;
    for(i=0; i<n; i++) {
      trip_ids[i] = (char*)malloc(20*sizeof(char));
      daymasks[i] = (int*)malloc(7*sizeof(int));

      fscanf(fp, 
             "%d %d %s %d %d %d %d %d %d %d\n", 
             departs+i, 
             arrives+i, 
             trip_ids[i], 
             daymasks[i]+0,
             daymasks[i]+1,
             daymasks[i]+2,
             daymasks[i]+3,
             daymasks[i]+4,
             daymasks[i]+5,
             daymasks[i]+6 );
    }

    gAddVertex( gg, from, NULL);
    gAddVertex( gg, to, NULL);
    gAddTripHopSchedule( gg, from, to, departs, arrives, trip_ids, daymasks, n );
   
    for(i=0; i<n; i++) {
      free(trip_ids[i]);
      free(daymasks[i]);
    }

    ct++;
  }
  fclose( fp );

  printf("reading links.out\n");
  fp = fopen( "links.out", "r" );

  while( !feof( fp ) ) {
    fscanf(fp, "%s %s\n", &from, &to);
    gAddVertex( gg, from, NULL );
    gAddVertex( gg, to, NULL );
    gAddLink( gg, from, to );
    gAddLink( gg, to, from );
  }
  fclose( fp );

  printf("graph loaded. Finding random path...\n");

  long fsize, rsize;
  CALLGRIND_START_INSTRUMENTATION;
//  struct prev_entry **forward_route = gShortestPath( gg, "MTSP6083", "MTSP5253", 11432, 0, &fsize );
  struct prev_entry **forward_route = gShortestPath( gg, "MTSP3500", "MTSP1", 29236, 1, &fsize );
  printf( "--==--\n" );
  struct prev_entry **retro_route = gShortestPath( gg, "MTSP3500", "MTSP1", 32667, 0, &rsize );
  CALLGRIND_STOP_INSTRUMENTATION;
  printf("path n:%d, %d found\n", fsize, rsize);

  int i;
  for(i=0; i<fsize; i++) {
    struct prev_entry *link = forward_route[i];
    printf("%s->%s\tdw: %ld\tt: %ld\tw: %ld\t via: %s\ttyp:%d\n", link->from, link->to, link->delta_weight, link->end_time, link->weight, link->desc, link->type);
    free(forward_route[i]);
  }
  free(forward_route);
  printf("--==--\n");
  for(i=0; i<rsize; i++) {
    struct prev_entry *link = retro_route[i];
    printf("%s->%s\tdw: %ld\tt: %ld\tw: %ld\tvia: %s\ttyp:%d\n", link->from, link->to, link->delta_weight, link->end_time, link->weight, link->desc, link->type);
    free(retro_route[i]);
  }
  free(retro_route);
  gDestroy( gg );

  printf("success\n");
  return 1;
}
