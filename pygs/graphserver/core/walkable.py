from ctypes import c_void_p
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core_original import State, WalkOptions


class Walkable:
    """Implements the walkable interface."""

    def __init__(self) -> None:
        self.soul: Optional[c_void_p] = None
        self._cwalk: Any = None
        self._cwalk_back: Any = None

    def walk(self, state: "State", walk_options: "WalkOptions") -> Optional["State"]:
        from ..core_original import State
        return State.from_pointer(self._cwalk(self.soul, state.soul, walk_options.soul))

    def walk_back(
        self, state: "State", walk_options: "WalkOptions"
    ) -> Optional["State"]:
        from ..core_original import State
        return State.from_pointer(
            self._cwalk_back(self.soul, state.soul, walk_options.soul)
        )