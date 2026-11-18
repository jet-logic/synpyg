import math
from copy import copy
from typing import Union, Any, Callable

from .timecmp import snap_time

INF = float("inf")


class Track:
    def __init__(
        self,
        hint_dur: float = 1.0,  # 1 sec
        current_time: float = 0,  # sec
        fps: float = 24.0,
        easing: Union[tuple[float, float, float, float], bool, None] = None,
    ):
        """``fps`` and ``easing`` are stored for callers; the built-in actions
        work in seconds and do not use them."""
        if not (math.isfinite(hint_dur) and hint_dur >= 0):
            raise ValueError(f"Invalid hint_dur {hint_dur}")
        if not (math.isfinite(current_time) and current_time >= 0):
            raise ValueError(f"Invalid time {current_time}")
        if not (math.isfinite(fps) and fps > 0):
            raise ValueError(f"Invalid fps {fps}")
        self.hint_dur = hint_dur
        self.current_time = current_time
        self.fps = fps
        self.easing = easing

    def advance(self, t: float):
        if not (math.isfinite(t) and t >= 0):
            raise ValueError(f"Invalid time {t}")
        new_time = snap_time(self.current_time + t)
        if not math.isfinite(new_time):
            raise ValueError(f"Invalid resulting time {new_time}")
        self.current_time = new_time
        return self

    def feed(self, cur: "Resolver"):
        s, e, f = cur(self.current_time, self.current_time, self.hint_dur)
        d = e - s
        if not d >= 0:  # also catches NaN; checked before f() so nothing is emitted
            raise ValueError(f"Invalid duration {d}")
        # Validate the resulting track time before running the finalizer: a
        # failed action must not emit waypoints or partially mutate its target.
        new_time = self.current_time
        if d < INF:
            new_time = snap_time(new_time + d)
            if not math.isfinite(new_time):
                raise ValueError(f"Invalid resulting time {new_time}")

        f(self, s, e)
        if d < INF:
            self.current_time = new_time
        return self

    def sub(self, o: float = 0.0):
        return copy(self).advance(o)

    def __lshift__(self, action: "Proxy"):
        # <<
        return self.feed(action(self))

    def __ilshift__(self, action: "Proxy"):
        # <<=
        return self.feed(action(self))

    def __matmul__(self, offset: float):
        # @
        return self.sub(offset * 1.0)


Finalizer = Callable[["Track", float, float], Any]
RangeEtc = tuple[float, float, Finalizer]
# A resolver is called as ``(start, base_time, hint_dur)``: ``base_time`` is the
# track time at which the whole action was fed; ``hint_dur`` is the default
# duration for items that do not state one.
Resolver = Callable[[float, float, float], RangeEtc]
Proxy = Callable[["Track"], Resolver]

# class Finalizer(Protocol):
#     def __call__(self, track: Track, start: float, end: float) -> Any: ...
