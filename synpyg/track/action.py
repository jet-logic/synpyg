import math
from numbers import Real
from typing import Any, Optional
from .timecmp import same_time as _same_time, snap_time
from .track import Finalizer, Proxy, RangeEtc, Resolver, Track, add_time

# Keywords that ToA/Add themselves pass to Animated.add_keyframe().
_RESERVED_TO_KWARGS = ("time", "value", "start")


def _number(x: Any, what: str, *, nonneg: bool = False) -> Optional[float]:
    """Coerce a real number (not a bool, not a string) to a finite float.

    ``None`` passes through. ``nonneg`` additionally rejects negative values."""
    if x is None:
        return None
    if isinstance(x, bool) or not isinstance(x, Real):
        raise TypeError(f"{what} must be a number of seconds, got {type(x).__name__}")
    try:
        f = float(x)
    except OverflowError:
        f = math.inf
    if not math.isfinite(f) or (nonneg and f < 0):
        raise ValueError(f"Invalid {what} {x!r}")
    return f


def _dur(x: Any) -> Optional[float]:
    return _number(x, "duration", nonneg=True)


def _check_targets(prop: Any) -> tuple:
    """Normalize a To/Add target (or list/tuple of targets) and check it.

    A target is anything with ``add_keyframe``.
    Checking here, rather than in the finalizer, means a wrong target is
    reported with a clear message before anything has been changed.
    """
    items = tuple(prop) if isinstance(prop, (list, tuple)) else (prop,)
    for item in items:
        if not callable(getattr(item, "add_keyframe", None)):
            raise TypeError(
                "To/Add target must be an Animated (or a list/tuple of them), "
                f"got {type(item).__name__}"
            )
    return items


def _check_to_kwargs(kwargs: dict, reserved: tuple = _RESERVED_TO_KWARGS) -> None:
    for k in reserved:
        if k in kwargs:
            raise ValueError(f"{k!r} is set by the action and cannot be passed")


def _noop(track: Track, start: float, end: float) -> None:
    pass


class _Item:
    """One resolved child of a Seq/Par: its resolver plus the range and
    finalizer it last resolved to, so containers can re-resolve it (ParE)
    and later run it."""

    __slots__ = ("resolver", "start", "end", "call")

    def __init__(self, resolver: Resolver) -> None:
        self.resolver = resolver
        self.start = self.end = 0.0
        self.call: Finalizer = _noop

    def resolve(self, start: float, base_time: float, hint_dur: float) -> None:
        self.start, self.end, self.call = self.resolver(start, base_time, hint_dur)


def _supply(items: list[_Item]) -> Finalizer:
    def supply(track: Track, start: float, end: float):
        for item in items:
            item.call(track, item.start, item.end)

    return supply


def PassA(track: Track, dur: Optional[float] = 1) -> Resolver:
    """Do nothing for ``dur`` seconds; ``dur=None`` uses the track's hint
    (as ``To`` does). The default is a fixed 1s, not the hint."""
    _d = _dur(dur)

    def resolve(start: float, base_time: float, hint_dur: float) -> RangeEtc:
        return start, add_time(start, hint_dur if _d is None else _d), _noop

    return resolve


def ToA(
    track: Track,
    prop: Any | tuple[Any],
    v: Any,
    dur: Optional[float] = None,
    **kwargs,
) -> Resolver:
    _items = _check_targets(prop)
    _check_to_kwargs(kwargs)
    _d = _dur(dur)

    def run(track: Track, s: float, e: float):
        for prop in _items:
            prop.add_keyframe(e, v, start=s, **kwargs)

    def resolve(start: float, base_time: float, hint_dur: float) -> RangeEtc:
        # A resolver fixes its duration the first time it is resolved. ParE
        # relies on this: it re-resolves an item at a new start, with a
        # different hint, and the item must keep the length it already has.
        nonlocal _d
        if _d is None:
            _d = hint_dur
        return start, add_time(start, _d), run

    return resolve


def AddA(*args, **kwargs):
    return ToA(*args, add=True, **kwargs)


def SeqA(
    track: Track,
    *args: Proxy,
    stagger: Optional[float] = None,
    delay: Optional[float] = None,
    dur: Optional[float] = None,
):
    if stagger is not None and delay is not None:
        raise ValueError("stagger and delay are mutually exclusive")
    _hint_dur = _dur(dur)
    _stagger = _number(stagger, "stagger")
    _delay = _number(delay, "delay")
    items = [_Item(sup(track)) for sup in args]

    def resolve(start: float, base_time: float, hint_dur: float):
        # An explicit ``dur`` replaces the hint passed down to the items;
        # without one, the hint from the enclosing action passes through.
        if _hint_dur is not None:
            hint_dur = _hint_dur
        s = end = start
        for item in items:
            item.resolve(s, base_time, hint_dur)
            end = max(end, item.end)  # the Seq lasts until its longest item ends
            # Next start: ``stagger`` is relative to this item's start, ``delay``
            # to its end, otherwise it follows directly. A negative offset
            # (overlap) never reaches back before the Seq itself.
            if _stagger is not None:
                s = max(add_time(s, _stagger), start)
            elif _delay is not None:
                s = max(add_time(item.end, _delay), start)
            else:
                s = item.end
        return start, end, _supply(items)

    return resolve


def ParA(
    track: Track,
    *args: Proxy,
    end: bool = False,
    dur: Optional[float] = None,
):
    _hint_dur = _dur(dur)
    items = [_Item(sup(track)) for sup in args]

    def resolve(start: float, base_time: float, hint_dur: float):
        # Items without a ``dur`` take the longest duration seen so far among
        # the items resolved before them, so the result depends on item order.
        d = _hint_dur
        last = start
        for item in items:
            item.resolve(start, base_time, hint_dur if d is None else d)
            length = item.end - item.start
            d = length if d is None else max(d, length)
            last = max(last, item.end)

        if end:  # ParE: re-resolve the shorter items so they all end together
            for item in items:
                if not _same_time(item.end, last):
                    item.resolve(
                        snap_time(last - (item.end - item.start)), base_time, d
                    )
        return start, last, _supply(items)

    return resolve


def Seq(
    *args: Proxy,
    stagger: Optional[float] = None,
    delay: Optional[float] = None,
    dur: Optional[float] = None,
) -> Proxy:
    return lambda track: SeqA(track, *args, stagger=stagger, delay=delay, dur=dur)


def Par(*args: Proxy, dur: Optional[float] = None) -> Proxy:
    return lambda track: ParA(track, *args, dur=dur)


def ParE(*args: Proxy, dur: Optional[float] = None) -> Proxy:
    return lambda track: ParA(track, *args, dur=dur, end=True)


def Pass(dur: Optional[float] = 1.0) -> Proxy:
    _dur(dur)  # fail where the action is written
    return lambda track: PassA(track, dur)


def To(
    prop: Any | tuple[Any],
    v: Any,
    dur: Optional[float] = None,
    **kwargs,
) -> Proxy:
    _check_targets(prop)
    _check_to_kwargs(kwargs)
    return lambda track: ToA(track, prop, v, dur, **kwargs)


def Add(
    prop: Any | tuple[Any],
    v: Any,
    dur: Optional[float] = None,
    **kwargs,
) -> Proxy:
    _check_targets(prop)
    _check_to_kwargs(kwargs, _RESERVED_TO_KWARGS + ("add",))
    return lambda track: AddA(track, prop, v, dur, **kwargs)


__all__ = ("Add", "To", "Pass", "Par", "ParE", "Seq")
