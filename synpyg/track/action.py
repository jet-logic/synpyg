import math
from numbers import Real
from typing import Optional, Any
from .timecmp import same_time as _same_time, snap_time
from .track import Finalizer, Proxy, RangeEtc, Resolver, Track

# Keywords that ToA/Add themselves pass to Animated.add_waypoint().
_RESERVED_TO_KWARGS = ("time", "value", "start")


def _add_time(start: float, duration: float) -> float:
    """Add a duration without silently turning finite time into infinity."""
    if math.isinf(duration):
        return math.inf
    result = start + duration
    if not math.isfinite(result):
        raise ValueError(f"Invalid resulting time {result}")
    return snap_time(result)


def _number(x: Any, what: str) -> float:
    """Coerce a real number (not a bool, not a string) to float."""
    if isinstance(x, bool) or not isinstance(x, Real):
        raise TypeError(f"{what} must be a number of seconds, got {type(x).__name__}")
    try:
        return float(x)
    except OverflowError:
        raise ValueError(f"Invalid {what} {x!r}") from None


def _check_dur(dur: Optional[float]) -> Optional[float]:
    """Coerce a duration to float seconds; reject negative and NaN (inf is allowed)."""
    if dur is None:
        return None
    dur = _number(dur, "duration")
    if not dur >= 0:
        raise ValueError(f"Invalid duration {dur}")
    return dur


def _check_offset(offset: Optional[float], name: str) -> Optional[float]:
    """Coerce a sequence offset to float seconds and reject non-finite values."""
    if offset is None:
        return None
    offset = _number(offset, name)
    if not math.isfinite(offset):
        raise ValueError(f"Invalid {name} {offset}")
    return offset


def _check_targets(prop: Any) -> tuple:
    """Normalize a To/Add target (or list/tuple of targets) and check it.

    A target is anything with ``add_waypoint`` (normally an ``Animated``).
    Checking here, rather than in the finalizer, means a wrong target is
    reported with a clear message before anything has been changed.
    """
    items = tuple(prop) if isinstance(prop, (list, tuple)) else (prop,)
    for item in items:
        if not callable(getattr(item, "add_waypoint", None)):
            raise TypeError(
                "To/Add target must be an Animated (or a list/tuple of them), "
                f"got {type(item).__name__}"
            )
    return items


def _check_to_kwargs(kwargs: dict, reserved: tuple = _RESERVED_TO_KWARGS) -> None:
    for k in reserved:
        if k in kwargs:
            raise ValueError(f"{k!r} is set by the action and cannot be passed")


def PassA(track: "Track", dur: Optional[float] = 1) -> Resolver:
    """Do nothing for ``dur`` seconds; ``dur=None`` uses the track's hint
    (as ``To`` does). The default is a fixed 1s, not the hint."""
    _dur = _check_dur(dur)

    def supply(track: "Track", start: float, end: float):
        pass

    def resolve(start: float, base_time: float, hint_dur: float) -> RangeEtc:
        return start, _add_time(start, hint_dur if _dur is None else _dur), supply

    return resolve


def ToA(
    track: "Track",
    prop: Any | tuple[Any],
    v: Any,
    dur: Optional[float] = None,
    **kwargs,
) -> Resolver:
    _items = _check_targets(prop)
    _check_to_kwargs(kwargs)
    _dur = _check_dur(dur)
    _extra = kwargs

    def run(track: "Track", s: float, e: float):
        for prop in _items:
            prop.add_waypoint(e, v, start=s, **_extra)

    def resolve(start: float, base_time: float, hint_dur: float) -> RangeEtc:
        # A resolver fixes its duration the first time it is resolved. ParE
        # relies on this: it re-resolves an item at a new start, with a
        # different hint, and the item must keep the length it already has.
        nonlocal _dur
        if _dur is None:
            _dur = hint_dur

        _end = _add_time(start, _dur)

        return start, _end, run

    return resolve


def AddA(*args, **kwargs):
    return ToA(*args, add=True, **kwargs)


def SeqA(
    track: "Track",
    *args: Proxy,
    stagger: Optional[float] = None,
    delay: Optional[float] = None,
    dur: Optional[float] = None,
):
    if stagger is not None and delay is not None:
        raise ValueError("stagger and delay are mutually exclusive")
    _hint_dur = _check_dur(dur)
    _stagger = _check_offset(stagger, "stagger")
    _delay = _check_offset(delay, "delay")
    res_head = llsup(track, *args)

    def resolve(start: float, base_time: float, hint_dur: float):
        # An explicit ``dur`` replaces the hint passed down to the items;
        # without one, the hint from the enclosing action passes through.
        dur = _hint_dur
        if dur is not None:
            hint_dur = dur
        res: Optional[_Item] = res_head
        e = start  # ending time
        if (o := _stagger) is not None:
            s = start  # starting time
            while res:
                p, q, f = res(s, base_time, hint_dur)
                e = max(e, q)  # the Seq lasts until its longest item ends
                res.start = p
                res.end = q
                res.call = f
                res = res.next
                # next start time; a negative stagger never reaches back
                # before the Seq itself
                s = max(_add_time(s, o), start)

        elif (o := _delay) is not None:
            s = start  # starting time
            while res:
                p, q, f = res(s, base_time, hint_dur)
                e = max(e, q)  # the Seq lasts until its longest item ends
                res.start = p
                res.end = q
                res.call = f
                res = res.next
                # next start: relative to this item's own end; a negative
                # delay (overlap) never reaches back before the Seq itself
                s = max(_add_time(q, o), start)
        else:
            while res:
                p, e, f = res(e, base_time, hint_dur)
                res.start = p
                res.end = e
                res.call = f
                res = res.next

        assert e >= start

        def supply(track: "Track", start: float, end: float):
            res: Optional[_Item] = res_head
            while res:
                res.call(track, res.start, res.end)
                res = res.next

        return start, e, supply

    return resolve


def _noop(track: "Track", start: float, end: float) -> None:
    pass


class _Item:
    """One resolved child of a Seq/Par, linked to its successor.

    Holds the child's resolver together with the range and finalizer it last
    resolved to, so containers can re-resolve it (ParE) and later run it.
    """

    __slots__ = ("resolver", "next", "start", "end", "call")

    def __init__(self, resolver: Resolver) -> None:
        self.resolver = resolver
        self.next: Optional["_Item"] = None
        self.start = 0.0
        self.end = 0.0
        self.call: Finalizer = _noop

    def __call__(self, start: float, base_time: float, hint_dur: float) -> RangeEtc:
        return self.resolver(start, base_time, hint_dur)


def llsup(track, *args: Proxy) -> Optional[_Item]:
    """Link the resolved items; returns None when there are none (a no-op)."""
    head = cur = None
    for sup in args:
        res = _Item(sup(track))
        if cur:
            cur.next = res
        else:
            head = res
        cur = res
    return head


def ParA(
    track: "Track",
    *args: Proxy,
    end: bool = False,
    dur: Optional[float] = None,
):
    _hint_dur = _check_dur(dur)
    res_head = llsup(track, *args)

    def resolve(start: float, base_time: float, hint_dur: float):
        # Items without a ``dur`` take the longest duration seen so far among
        # the items resolved before them, so the result depends on item order.
        dur = _hint_dur
        E = start
        res: Optional[_Item] = res_head
        while res:
            p, q, f = res(start, base_time, hint_dur if dur is None else dur)
            if dur is None:
                dur = q - p
            else:
                dur = max(dur, q - p)
            E = max(E, q)
            res.start = p
            res.end = q
            res.call = f
            res = res.next

        if end and res_head:
            assert dur is not None
            res = res_head
            while res:
                if not _same_time(res.end, E):
                    p, q, f = res(snap_time(E - (res.end - res.start)), base_time, dur)
                    res.start = p
                    res.end = q
                    res.call = f
                # internal invariants, up to float noise
                assert _same_time(res.end, E)
                assert res.start >= start or _same_time(res.start, start)
                res = res.next
        assert E >= start

        def supply(track: "Track", start: float, end: float):
            res: Optional[_Item] = res_head
            while res:
                # res.call(track)
                res.call(track, res.start, res.end)
                res = res.next

        return start, E, supply

    return resolve


def Seq(
    *args: Proxy,
    stagger: Optional[float] = None,
    delay: Optional[float] = None,
    dur: Optional[float] = None,
) -> Proxy:
    return lambda track: SeqA(track, *args, stagger=stagger, delay=delay, dur=dur)


def Par(
    *args: Proxy,
    dur: Optional[float] = None,
) -> Proxy:
    return lambda track: ParA(track, *args, dur=dur)


def ParE(
    *args: Proxy,
    dur: Optional[float] = None,
) -> Proxy:
    return lambda track: ParA(track, *args, dur=dur, end=True)


def Pass(dur: Optional[float] = 1.0) -> Proxy:
    _check_dur(dur)  # fail where the action is written
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
