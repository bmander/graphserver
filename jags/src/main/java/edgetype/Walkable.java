package edgetype;

import core.State;
import core.WalkOptions;
import core.WalkResult;

public interface Walkable{
    WalkResult walk( State s0, WalkOptions wo );
    WalkResult walkBack( State s0, WalkOptions wo );
}

