import math
from typing import Optional, Protocol, Any, Union
from .track import Finalizer, Proxy, RangeEtc, Resolver, Track


# Same tolerances as Animated uses for "the same instant": float noise only.
_TIME_ABS_TOL = 1e-9
_TIME_REL_TOL = 1e-12


def _same_time(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=_TIME_REL_TOL, abs_tol=_TIME_ABS_TOL)


def _check_dur(dur: Optional[float]) -> Optional[float]:
    """Coerce a duration to float; reject negative and NaN (inf is allowed)."""
    if dur is None:
        return None
    dur = dur * 1.0
    if not dur >= 0:
        raise ValueError(f"Invalid duration {dur}")
    return dur


def _check_offset(offset: Optional[float], name: str) -> Optional[float]:
    """Coerce a sequence offset to float and reject non-finite values."""
    if offset is None:
        return None
    offset = offset * 1.0
    if not math.isfinite(offset):
        raise ValueError(f"Invalid {name} {offset}")
    return offset


def PassA(track: "Track", dur: float = 1, **kwargs) -> Resolver:
    dur = _check_dur(dur)

    def supply(track: "Track", start: float, end: float):
        pass

    def resolve(start: float, base_frame: float, hint_dur: float) -> RangeEtc:
        return start, start + dur, supply

    return resolve


def ToA(
    track: "Track",
    prop: Any | tuple[Any],
    v: Any,
    dur: Union[float, None] = None,
    **kwargs,
) -> Resolver:
    if isinstance(prop, (list, tuple)):
        _items = prop
    else:
        _items = (prop,)
    _dur = _check_dur(dur)
    _extra = kwargs

    def run(track: "Track", s: float, e: float):
        for prop in _items:
            prop.add_waypoint(e, v, start=s, **_extra)

    def resolve(start: float, base_frame: float, hint_dur: float) -> RangeEtc:
        nonlocal _dur
        if _dur is None:
            _dur = hint_dur

        _end = start + _dur

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

    def resolve(start: float, base_frame: float, hint_dur: float):
        # Note: hint_dur=None to stop it from propagating to sub items
        dur = _hint_dur
        if dur is not None:
            hint_dur = dur
        res: Optional[Wrapper] = res_head
        e = start  # ending time
        if (o := _stagger) is not None:
            s = start  # starting time
            while res:
                p, q, f = res(s, base_frame, hint_dur)
                e = max(e, q)  # the Seq lasts until its longest item ends
                res.start = p
                res.end = q
                res.call = f
                res = res.next
                # next start time; a negative stagger never reaches back
                # before the Seq itself
                s = max(s + o, start)

        elif (o := _delay) is not None:
            s = start  # starting time
            while res:
                p, q, f = res(s, base_frame, hint_dur)
                e = max(e, q)  # the Seq lasts until its longest item ends
                res.start = p
                res.end = q
                res.call = f
                res = res.next
                # next start: relative to this item's own end; a negative
                # delay (overlap) never reaches back before the Seq itself
                s = max(q + o, start)
        else:
            while res:
                p, e, f = res(e, base_frame, hint_dur)
                res.start = p
                res.end = e
                res.call = f
                res = res.next

        assert e >= start

        def supply(track: "Track", start: float, end: float):
            res: Optional[Wrapper] = res_head
            while res:
                res.call(track, res.start, res.end)
                res = res.next

        return start, e, supply

    return resolve


class Wrapper(Protocol):
    next: Optional["Wrapper"]
    start: float
    end: float
    call: Finalizer

    def __call__(self, start: float, base_frame: float, hint_dur: float) -> RangeEtc:
        raise NotImplementedError()


def llsup(track, *args: Proxy) -> Optional[Wrapper]:
    """Link the resolved items; returns None when there are none (a no-op)."""
    head = cur = None
    for sup in args:
        res: Wrapper = sup(track)  # type: ignore
        if cur:
            cur.next = res
        else:
            head = cur = res
        res.next = None
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

    def resolve(start: float, base_frame: float, hint_dur: float):
        dur = _hint_dur
        E = start
        res: Optional[Wrapper] = res_head
        while res:
            p, q, f = res(start, base_frame, hint_dur if dur is None else dur)
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
                    p, q, f = res(E - (res.end - res.start), base_frame, dur)
                    res.start = p
                    res.end = q
                    res.call = f
                # internal invariants, up to float noise
                assert _same_time(res.end, E)
                assert res.start >= start or _same_time(res.start, start)
                res = res.next
        assert E >= start

        def supply(track: "Track", start: float, end: float):
            res: Optional[Wrapper] = res_head
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


def Pass(dur=1.0) -> Proxy:
    return lambda track: PassA(track, dur)


def To(
    prop: Any | tuple[Any],
    v: Any,
    dur: Union[float, None] = None,
    **kwargs,
) -> Proxy:
    return lambda track: ToA(track, prop, v, dur, **kwargs)


def Add(
    prop: Any | tuple[Any],
    v: Any,
    dur: Union[float, None] = None,
    **kwargs,
) -> Proxy:
    return lambda track: ToA(track, prop, v, dur, add=True, **kwargs)


__all__ = ("Add", "To", "Pass", "Par", "ParE", "Seq")
