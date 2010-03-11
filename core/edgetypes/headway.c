
//HEADWAY FUNCTIONS

Headway*
headwayNew(int begin_time, int end_time, int wait_period, int transit, char* trip_id, ServiceCalendar* calendar, Timezone* timezone, int agency, ServiceId service_id) {
    Headway* ret = (Headway*)malloc(sizeof(Headway));
    
    ret->type = PL_HEADWAY;
    ret->begin_time = begin_time;
    ret->end_time = end_time;
    ret->wait_period = wait_period;
    ret->transit = transit;
    int n = strlen(trip_id)+1;
    ret->trip_id = (char*)malloc(sizeof(char)*(n));
    memcpy(ret->trip_id, trip_id, n);
    ret->calendar = calendar;
    ret->timezone = timezone;
    ret->agency = agency;
    ret->service_id = service_id;
    
    //bind functions to methods
    ret->walk = &headwayWalk;
    ret->walkBack = &headwayWalkBack;
    
    return ret;
}

void
headwayDestroy(Headway* tokill) {
  free(tokill->trip_id);
  free(tokill);
}

int
headwayBeginTime(Headway* this) { return this->begin_time; }

int
headwayEndTime(Headway* this) { return this->end_time; }

int
headwayWaitPeriod(Headway* this) { return this->wait_period; }

int
headwayTransit(Headway* this) { return this->transit; }

char*
headwayTripId(Headway* this) { return this->trip_id; }

ServiceCalendar*
headwayCalendar(Headway* this) { return this->calendar; }

Timezone*
headwayTimezone(Headway* this) { return this->timezone; }

int
headwayAgency(Headway* this) { return this->agency; }

ServiceId
headwayServiceId(Headway* this) { return this->service_id; }