#ifndef _WALKOPTIONS_H_
#define _WALKOPTIONS_H_

//---------------DECLARATIONS FOR WALKOPTIONS CLASS---------------

struct WalkOptions {
    int transfer_penalty;
    float walking_speed;
    float walking_reluctance;
    float uphill_slowness;
    float downhill_fastness;
    float phase_change_grade;
    float hill_reluctance;    
    int max_walk;
    float walking_overage;
    int turn_penalty;
    
    float phase_change_velocity_factor;
} ;

WalkOptions*
woNew(void);

void
woDestroy( WalkOptions* this );

int
woGetTransferPenalty( WalkOptions* this );

void
woSetTransferPenalty( WalkOptions* this, int transfer_penalty );

float
woGetWalkingSpeed( WalkOptions* this );

void
woSetWalkingSpeed( WalkOptions* this, float walking_speed );

float
woGetWalkingReluctance( WalkOptions* this );

void
woSetWalkingReluctance( WalkOptions* this, float walking_reluctance );

int
woGetMaxWalk( WalkOptions* this );

void
woSetMaxWalk( WalkOptions* this, int max_walk );

float
woGetWalkingOverage( WalkOptions* this );

void
woSetWalkingOverage( WalkOptions* this, float walking_overage );

int
woGetTurnPenalty( WalkOptions* this );

void
woSetTurnPenalty( WalkOptions* this, int turn_penalty );

#endif
