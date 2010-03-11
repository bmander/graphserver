
#include "graphserver.h"

//---------------DEFINITIONS FOR WALKOPTIONS CLASS---------------

WalkOptions*
woNew() {
    WalkOptions* ret = (WalkOptions*)malloc( sizeof(WalkOptions) );
    ret->transfer_penalty = 0;
    ret->turn_penalty = 0;
    ret->walking_speed = 6.07; //meters per second
    ret->walking_reluctance = 1;
    ret->uphill_slowness = 0.05; //Factor by which someone's speed is slowed going uphill.
    ret->downhill_fastness = -12.1; // meters per second per grade percentage
    ret->phase_change_grade = 0.045; // Grade. An interesting thing happens at a particular grade, when they settle in for a long slog.
    ret->hill_reluctance = 0; //Factor by which an uphill stretch is penalized, in addition to whatever time is lost by simply gaining.
    ret->max_walk = 10000; //meters
    ret->walking_overage = 0.1;
    
    // velocity between 0 grade and the phase change grade is Ax^2+Bx+C, where A is the phase_change_velocity_factor, B is the downhill fastness, and C is the average speed
    float phase_change_speed = (ret->uphill_slowness*ret->walking_speed)/(ret->uphill_slowness+ret->phase_change_grade);
    ret->phase_change_velocity_factor = (phase_change_speed - ret->downhill_fastness*ret->phase_change_grade - ret->walking_speed)/(ret->phase_change_grade*ret->phase_change_grade);
        
    return ret;
}

void
woDestroy( WalkOptions* this ) {
    free(this);
}

int
woGetTransferPenalty( WalkOptions* this ) {
    return this->transfer_penalty;
}

void
woSetTransferPenalty( WalkOptions* this, int transfer_penalty ) {
    this->transfer_penalty = transfer_penalty;
}

float
woGetWalkingSpeed( WalkOptions* this ) {
    return this->walking_speed;
}

void
woSetWalkingSpeed( WalkOptions* this, float walking_speed ) {
    this->walking_speed = walking_speed;
}

float
woGetWalkingReluctance( WalkOptions* this ) {
    return this->walking_reluctance;
}

void
woSetWalkingReluctance( WalkOptions* this, float walking_reluctance ) {
    this->walking_reluctance = walking_reluctance;
}

float
woGetUphillSlowness( WalkOptions* this ) {
    return this->uphill_slowness;
}

void
woSetUphillSlowness( WalkOptions* this, float uphill_slowness ) {
    this->uphill_slowness = uphill_slowness;
}

float
woGetDownhillFastness( WalkOptions* this ) {
    return this->downhill_fastness;
}

void
woSetDownhillFastness( WalkOptions* this, float downhill_fastness ) {
    this->downhill_fastness = downhill_fastness;
}

float
woGetHillReluctance( WalkOptions* this ) {
    return this->hill_reluctance;
}

void
woSetHillReluctance( WalkOptions* this, float hill_reluctance ) {
    this->hill_reluctance = hill_reluctance;
}

int
woGetMaxWalk( WalkOptions* this ) {
    return this->max_walk;
}

void
woSetMaxWalk( WalkOptions* this, int max_walk ) {
    this->max_walk = max_walk;
}

float
woGetWalkingOverage( WalkOptions* this ) {
    return this->walking_overage;
}

void
woSetWalkingOverage( WalkOptions* this, float walking_overage ) {
    this->walking_overage = walking_overage;
}

int
woGetTurnPenalty( WalkOptions* this ) {
    return this->turn_penalty;
}

void
woSetTurnPenalty( WalkOptions* this, int turn_penalty ) {
    this->turn_penalty = turn_penalty;
}