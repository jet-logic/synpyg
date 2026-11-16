from typing import Union, Any, Callable

INF = float("inf")


class Track:

    def __init__(
        self,
        hint_dur: float = 1.0,  # 1 sec
        end_frame: float = 0,  # sec
        fps: float = 24.0,
        easing: Union[tuple[float, float, float, float], bool, None] = None,
    ):
        self.hint_dur = hint_dur
        self.end_frame = end_frame
        self.fps = fps
        self.easing = easing

    def advance(self, t: float):
        self.end_frame += t
        return self

    def feed(self, cur: "Resolver"):
        s, e, f = cur(self.end_frame, self.end_frame, self.hint_dur)
        f(self, s, e)
        d = e - s
        if d < INF:
            self.end_frame += d
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
__all__ = ("Track",)
