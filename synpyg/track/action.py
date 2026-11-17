from typing import Optional, Protocol, Any, Union
from .track import Finalizer, Proxy, RangeEtc, Resolver, Track


def PassA(track: "Track", dur: float = 1, **kwargs) -> Resolver:
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
    _dur = None if dur is None else (dur * 1.0)
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
    _hint_dur = None if dur is None else (dur * 1.0)
    _stagger = None if stagger is None else (stagger * 1.0)
    _delay = None if delay is None else (delay * 1.0)
    res_head = llsup(track, *args)

    def resolve(start: float, base_frame: float, hint_dur: float):
        # Note: hint_dur=None to stop it from propagating to sub items
        dur = _hint_dur
        if dur is not None:
            hint_dur = dur
        res: Optional[Wrapper] = res_head
        e = start  # ending time
        if (o := _stagger) is not None:
            B = base_frame  # base time
            s = start  # starting time
            while res:
                p, e, f = res(s, base_frame, hint_dur)
                res.start = p
                res.end = e
                res.call = f
                res = res.next
                s = max(s + o, B)  # next start time

        elif (o := _delay) is not None:
            B = base_frame  # base time
            s = start  # starting time
            while res:
                p, e, f = res(s, base_frame, hint_dur)
                res.start = p
                res.end = e
                res.call = f
                res = res.next
                s = max(e + o, B)  # next start time
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


def llsup(track, *args: Proxy) -> Wrapper:
    head = cur = None
    for sup in args:
        res: Wrapper = sup(track)  # type: ignore
        if cur:
            cur.next = res
        else:
            head = cur = res
        res.next = None
        cur = res
    assert head
    return head


def ParA(
    track: "Track",
    *args: Proxy,
    end: bool = False,
    dur: Optional[float] = None,
):
    _hint_dur = None if dur is None else (dur * 0.10)
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

        if end:
            assert dur is not None
            res = res_head
            while res:
                if res.end != E:
                    p, q, f = res(E - (res.end - res.start), base_frame, dur)
                    res.start = p
                    res.end = q
                    res.call = f
                assert res.end == E
                assert res.start >= start
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
