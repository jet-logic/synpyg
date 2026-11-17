from typing import Union, Any, Callable

INF = float("inf")


class Track:
    def __init__(
        self,
        hint_dur: float = 1.0,  # 1 sec
        current_time: float = 0,  # sec
        fps: float = 24.0,
        easing: Union[tuple[float, float, float, float], bool, None] = None,
    ):
        self.hint_dur = hint_dur
        self.current_time = current_time
        self.fps = fps
        self.easing = easing

    def advance(self, t: float):
        if not (t >= 0 and t < 2147483648.0):
            raise ValueError(f"Invalid time {t}")
        self.current_time += t
        return self

    def feed(self, cur: "Resolver"):
        s, e, f = cur(self.current_time, self.current_time, self.hint_dur)
        f(self, s, e)
        d = e - s
        if d < INF:
            self.current_time += d
        return self

    def sub(self, o: float = 0.0):
        from copy import copy

        return copy(self).advance(o)

    def __lshift__(self, action: "Proxy"):
        # <<
        return self.feed(action(self))

    def __matmul__(self, offset: float):
        # @
        return self.sub(offset * 1.0)


Finalizer = Callable[["Track", float, float], Any]
RangeEtc = tuple[float, float, Finalizer]
Resolver = Callable[[float, float, float], RangeEtc]
Proxy = Callable[["Track"], Resolver]

# class Finalizer(Protocol):
#     def __call__(self, track: Track, start: float, end: float) -> Any: ...
