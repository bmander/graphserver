#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../graphserver.h"
#include "../graph.h"
#include <valgrind/callgrind.h>

int main() {

    Graph* gg = gNew();
    ServiceCalendar* sc = scNew();
    ServiceId sid = 0;
    ServicePeriod* sp = spNew( 0, 1000000, 1, &sid );
    scAddPeriod( sc, sp );
    TimezonePeriod *tzp = tzpNew( 0, 1000000, 0 );
    Timezone *tz = tzNew();
    tzAddPeriod( tz, tzp );
    
    FILE* fp = fopen( "hopslines", "r" );
    char* fromv = (char*)malloc(255*sizeof(char));
    char* frompsv = (char*)malloc(255*sizeof(char));
    char* topsv = (char*)malloc(255*sizeof(char));
    char* tov = (char*)malloc(255*sizeof(char));
    char* tripid = (char*)malloc(255*sizeof(char));
    int depart;
    int crossing;
    int arrive;
    int i = 0;
    while(!feof(fp)) {
        fscanf( fp, "%s %s %s %s %s %d %d %d", fromv, frompsv, topsv, tov, tripid, &depart, &crossing, &arrive );
        printf( "%s %s %s %s %s %d %d %d\n",fromv, frompsv, topsv, tov, tripid, depart, crossing, arrive);
        
        gAddVertex( gg, fromv );
        gAddVertex( gg, tov );
        gAddVertex( gg, frompsv );
        gAddVertex( gg, topsv );
        
        TripBoard* tb = tbNew( 0, sc, tz, 0 );
        tbAddBoarding(tb, tripid, depart, 0);
        gAddEdge( gg, fromv, frompsv, (EdgePayload*)tb );
        
        Crossing* cr = crNew( );
        gAddEdge( gg, frompsv, topsv, (EdgePayload*)cr );
        
        TripAlight* al = alNew( 0, sc, tz, 0 );
        alAddAlighting( al, tripid, arrive, 0 );
        gAddEdge( gg, topsv, tov, (EdgePayload*)al );
        
    }
    
    
    //clean up
    free(fromv);
    free(frompsv);
    free(tov);
    free(topsv);
    free(tripid);
    
    tzDestroy(tz);
    scDestroy(sc);
    fclose( fp );
    gDestroy( gg );
    return 1;
}
