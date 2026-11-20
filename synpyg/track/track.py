import math
from copy import copy
from typing import Any, Callable

from .timecmp import snap_time


def check_time(x: float, what: str = "time") -> float:
    """Times and durations are finite floats >= 0 (this also rejects NaN)."""
    if not (math.isfinite(x) and x >= 0):
        raise ValueError(f"Invalid {what} {x}")
    return x


def add_time(t: float, d: float) -> float:
    """``t + d`` snapped to the time grid; the result must stay finite."""
    result = snap_time(t + d)
    if not math.isfinite(result):
        raise ValueError(f"Invalid resulting time {result}")
    return result


class Track:
    def __init__(
        self,
        hint_dur: float = 1.0,  # 1 sec
        current_time: float = 0,  # sec
    ):
        """Everything on a track is in seconds; convert frames before use."""
        self.hint_dur = check_time(hint_dur, "hint_dur")
        self.current_time = check_time(current_time)

    def advance(self, t: float):
        self.current_time = add_time(self.current_time, check_time(t))
        return self

    def feed(self, cur: "Resolver"):
        s, e, f = cur(self.current_time, self.current_time, self.hint_dur)
        if not e - s >= 0:  # also catches NaN
            raise ValueError(f"Invalid duration {e - s}")
        # Validate the new track time before running the finalizer: a failed
        # action must not emit keyframes or partially mutate its target.
        new_time = add_time(self.current_time, e - s)
        f(self, s, e)
        self.current_time = new_time
        return self

    def sub(self, o: float = 0.0):
        return copy(self).advance(o)

    def __lshift__(self, action: "Proxy"):  # track << action
        return self.feed(action(self))

    __ilshift__ = __lshift__  # track <<= action

    def __matmul__(self, offset: float):  # track @ offset
        return self.sub(offset * 1.0)


Finalizer = Callable[["Track", float, float], Any]
RangeEtc = tuple[float, float, Finalizer]
# A resolver is called as ``(start, base_time, hint_dur)``: ``base_time`` is the
# track time at which the whole action was fed; ``hint_dur`` is the default
# duration for items that do not state one.
Resolver = Callable[[float, float, float], RangeEtc]
Proxy = Callable[["Track"], Resolver]
