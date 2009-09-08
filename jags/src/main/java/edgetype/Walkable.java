package main.java.edgetype;

import main.java.core.State;
import main.java.core.WalkOptions;
import main.java.core.WalkResult;

public interface Walkable{
    WalkResult walk( State s0, WalkOptions wo );
    WalkResult walkBack( State s0, WalkOptions wo );
}

