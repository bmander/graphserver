#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../core/graph.h"
#include <valgrind/callgrind.h>

int main() {
    
    Graph* gg = gNew(); 
    
    FILE* fp = fopen("transit.txt", "r");
    
    // Load up the calendar
    int ncaldays;
    fscanf( fp, "%d\n", &ncaldays );

    //printf( "%d\n", ncaldays );
    
    ServiceCalendar* cal = scNew();
    int i;
    for(i=0; i<ncaldays; i++) {
        long daystart;
        long dayend;
        int nserviceids;
        int daylightsavings;
        fscanf( fp, "%ld %ld %d %d\n", &daystart, &dayend, &nserviceids, &daylightsavings );
        //printf( "%ld %ld %d\n", daystart, dayend, nserviceids );
        
        int serviceids[nserviceids];
        int j;
        for(j=0; j<nserviceids; j++) {
            int service_id;
            fscanf( fp, "%d\n", &service_id );
            serviceids[j]=service_id;
            //printf( "%d\n", service_id);
        }
        
        scAddPeriod( cal, spNew( daystart, dayend, nserviceids, serviceids ) );
    }
    
    //Load up vertices
    int nvertices;
    fscanf( fp, "%d\n", &nvertices );
    //printf( "%d\n", nvertices );
    
    for(i=0; i<nvertices; i++) {
        char label[40];
        fscanf( fp, "%s\n", &label );
        //printf( "%s\n", label );
        gAddVertex(gg, label );
    }
    

    Timezone* tz = tzNew();
    TimezonePeriod* tzp = tzpNew(0, 1581602400, -8*3600);
    tzAddPeriod(tz, tzp);
    
    //Load up triphopschedules
    //for each vertex
    for(i=0; i<nvertices; i++) {
        char label[40];
        int noutgoing;
        fscanf( fp, "%s %d\n", &label, &noutgoing );
        //printf( "%s %d\n", label, noutgoing );
        
        //for each outgoing edge
        int j;
        for(j=0; j<noutgoing; j++) {
            char destlabel[40];
            int service_id;
            int timezone_offset;
            int nhops;
            
            fscanf( fp, "%s %d %d %d\n", &destlabel, &service_id, &timezone_offset, &nhops );
            //printf( "%s %d %d %d\n", destlabel, service_id, timezone_offset, nhops );
            
            int departs[nhops];
            int arrives[nhops];
            char* trip_ids[nhops];
            
            //for each triphop
            int k;
            for(k=0; k<nhops; k++) {
                int depart;
                int arrive;
                char trip_id[40];
                
                fscanf( fp, "%d %d %s\n", &depart, &arrive, &trip_id );
                //printf( "%d %d %s\n", depart, arrive, trip_id );
                
                departs[k] = depart;
                arrives[k] = arrive;
                trip_ids[k] = trip_id;
            }
            
            TripHopSchedule* ths = thsNew( departs, arrives, trip_ids, nhops, service_id, cal, tz, 0 );
            
            gAddEdge( gg, label, destlabel, (EdgePayload*)ths );
            
        }
    }
    
    fclose( fp );
    
    
    long t = 1215674100; //#Wed 2008-7-9 11:15:00 PST-0800
    Graph* spt = gShortestPathTree( gg, "16TH", "bogus", stateNew( 1, t ), 1 );
    
    gDestroy( spt, 1, 0 );
    
    gDestroy(gg, 1, 1);

    scDestroy( cal );
    
    tzDestroy( tz );
    
    
    
    return 1;
} 
