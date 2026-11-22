from .attrs import FloatAttr, StringAttr, StringEnumAttr, TimeAttr
from .ref import Ref
from .timeutil import tosec
from .value import Value, ValueKind
from .base import WithFields, WithXML
from .track.timecmp import same_time as _same_time

VALID_INTERPOLATIONS = (
    "auto",
    "clamped",
    "constant",
    "ease",
    "halt",
    "linear",
    "manual",
)


def _map_values(fn, *values):
    """Apply a scalar operation recursively to scalar/tuple value data."""
    first = values[0]
    if isinstance(first, tuple):
        return tuple(
            _map_values(fn, *(v[i] for v in values)) for i in range(len(first))
        )
    return fn(*values)


def _scale(value, factor):
    return _map_values(lambda x: x * factor, value)


def _add(*values):
    return _map_values(lambda *xs: sum(xs), *values)


def _sub(a, b):
    return _map_values(lambda x, y: x - y, a, b)


def _component_clamped_tangent(p0, p1, p2, t0, t1, t2):
    """Synfig's component-wise clamped tangent calculation."""
    if t2 == t0:
        return 0.0
    projected = p0 + (p2 - p0) * (t1 - t0) / (t2 - t0)
    if p2 > p0:
        if p1 >= p2 or p1 <= p0:
            return 0.0
        if p1 > projected:
            bias = (projected - p1) / (p2 - projected)
        elif p1 < projected:
            bias = (projected - p1) / (projected - p0)
        else:
            bias = 0.0
    elif p0 > p2:
        if p1 >= p0 or p1 <= p2:
            return 0.0
        if p1 > projected:
            bias = (projected - p1) / (projected - p0)
        elif p1 < projected:
            bias = (projected - p1) / (p2 - projected)
        else:
            bias = 0.0
    else:
        return 0.0
    return (p1 - p0) * (1.0 + bias) / 2.0 + (p2 - p1) * (1.0 - bias) / 2.0


def _clamped_tangent(p0, p1, p2, t0, t1, t2):
    return _map_values(_component_clamped_tangent, p0, p1, p2, t0, t1, t2)


def _hermite(p0, p1, m0, m1, u):
    u2, u3 = u * u, u * u * u
    return _add(
        _scale(p0, 2 * u3 - 3 * u2 + 1),
        _scale(m0, u3 - 2 * u2 + u),
        _scale(p1, -2 * u3 + 3 * u2),
        _scale(m1, u3 - u2),
    )


class Waypoint(WithFields, WithXML):
    # users are expected to use Animated.add_keyframe,
    value: Value | Ref  # child element (or `use`), not an XML attribute, so not a Field
    time = TimeAttr(required=True)
    before = StringEnumAttr(choices=VALID_INTERPOLATIONS)
    after = StringEnumAttr(choices=VALID_INTERPOLATIONS)
    tension = FloatAttr()
    temporal_tension = FloatAttr(name="temporal-tension")
    continuity = FloatAttr()
    bias = FloatAttr()

    def to_xml_element(self, et):
        try:
            value = self.value
        except AttributeError:
            at = self.__dict__.get("time")
            raise ValueError(
                "Waypoint has no value" + (f" (time={at!r})" if at is not None else "")
            ) from None
        if not isinstance(value, (Value, Ref)):
            raise TypeError(
                f"Waypoint value must be a Value or a Ref, got {type(value).__name__}"
            )
        if isinstance(value, Ref):  # `use` and a child element exclude each other
            return et.Element("waypoint", {**self._xml_attrs(), "use": value.use})
        element = et.Element("waypoint", self._xml_attrs())
        element.append(value.to_xml_element(et))
        return element

    def __repr__(self) -> str:
        d = self.__dict__
        parts = [f"{k}={d[k]!r}" for k in ("time", "value") if k in d]
        parts += [f"{k}={v!r}" for k, _, v in self._enum_fields() if k != "time"]
        return f"Waypoint({', '.join(parts)})"


def _latest(waypoints: list[Waypoint]) -> Waypoint:
    """The latest waypoint in time (the last one inserted, among equal times)."""
    return max(reversed(waypoints), key=lambda wp: wp.time)


class Animated(WithFields):
    kind: ValueKind

    id = StringAttr()
    guid = StringAttr()
    interpolation = StringEnumAttr(choices=VALID_INTERPOLATIONS)

    def __init__(
        self, kind: ValueKind | type[Value], *, id=None, guid=None, interpolation=None
    ):
        super().__init__()

        kind = ValueKind.of(kind)
        if not kind.tag:
            raise TypeError(f"{kind.name} has no tag and cannot be animated")

        self.kind = kind
        self.waypoints: list[Waypoint] = []

        self._assign_given(id=id, guid=guid, interpolation=interpolation)

    def __repr__(self) -> str:
        parts = [self.kind.name]
        parts += [f"{k}={v!r}" for k, _, v in self._enum_fields()]
        parts.append(f"waypoints={len(self.waypoints)}")
        return f"Animated({', '.join(parts)})"

    def _xml_attrs(self) -> dict[str, str]:
        attrs = super()._xml_attrs()
        for k in ("id", "guid"):  # an empty id means "none", as for Value
            if attrs.get(k) == "":
                del attrs[k]
        return attrs

    def _reject_self_reference(self, value) -> None:
        if isinstance(value, Ref) and value.target is self:
            raise ValueError("an Animated cannot refer to itself")

    def _check_waypoint(self, w) -> None:
        """Validate a waypoint that may have bypassed ``add_keyframe``."""
        if not isinstance(w, Waypoint):
            raise TypeError(
                f"waypoints must hold Waypoint objects, got {type(w).__name__}"
            )
        value = w.__dict__.get("value")
        if value is None:
            return  # Waypoint.to_xml_element reports the missing value
        at = w.__dict__.get("time")
        if isinstance(value, Ref):
            try:
                value.check_kind(self.kind)
            except ValueError as e:
                raise ValueError(f"waypoint at {at!r}s: {e}") from None
            self._reject_self_reference(value)
        elif isinstance(value, Value) and not isinstance(value, self.kind.value_type):
            raise ValueError(
                f"waypoint at {at!r}s holds {type(value).__name__}, "
                f"but this Animated is of kind {self.kind.name}"
            )
        # anything else is reported by Waypoint.to_xml_element

    def to_xml_element(self, et):
        for w in self.waypoints:  # the list is public, so don't trust it
            self._check_waypoint(w)
        attrs = {"type": self.kind.tag, **self._xml_attrs()}
        element = et.Element("animated", attrs)

        for child in self._ordered_waypoints():
            element.append(child.to_xml_element(et))

        return element

    def add_keyframe(
        self,
        time,
        value,
        *,
        add=False,
        start: float | str | None = None,
        **kwargs,
    ):
        """Add a waypoint. ``time`` may be seconds or a time string such as
        "1.5s", "500ms" or "1:30"; frames ("12f") are not accepted. Times are
        always finite floats.

        ``start`` is the time an interpolation towards this waypoint begins
        (supplied by the ``To`` action). If no waypoint sits at ``start``, a
        hold waypoint is inserted there carrying the value of the latest
        waypoint before it, so the move starts at ``start`` instead of at an
        earlier keyframe. Note this is that waypoint's own value, not the
        interpolated value, which differs when later waypoints exist."""
        w = Waypoint()
        w.time = t = tosec(time)
        w.value = v = self.kind.coerce(value)
        self._reject_self_reference(v)
        w._assign_given(**kwargs)  # None leaves a field unset, as in Animated(...)

        hold = None
        if start is not None:
            start = tosec(start)
            if not _same_time(start, t):
                if start > t:
                    raise ValueError(
                        f"start time {start!r}s is after waypoint time {t!r}s"
                    )
                if not any(_same_time(wp.time, start) for wp in self.waypoints):
                    earlier = [wp for wp in self.waypoints if wp.time < start]
                    if earlier:
                        hold = Waypoint()
                        hold.time = start
                        hold.value = _latest(earlier).value

        merge = None  # an existing waypoint at the same time absorbs this one
        if add:
            if not self.waypoints:
                raise ValueError("No previous waypoint")
            last = _latest(self.waypoints)
            if _same_time(t, last.time):
                merge = last
            elif t < last.time:
                raise ValueError(
                    f"time must be incremental: {t!r}s is before the "
                    f"previous waypoint at {last.time!r}s"
                )
            w.value = self.kind.add(last.value, v)

        if hold is not None:
            self.waypoints.append(hold)
        if merge is None:
            self.waypoints.append(w)
        else:
            merge.value = w.value
            merge._assign_given(**kwargs)
        return self

    def _ordered_waypoints(self) -> list[Waypoint]:
        return sorted(self.waypoints, key=lambda w: w.time)  # stable

    def at(self, time: float) -> Value:
        """Evaluate the animation at ``time`` (seconds).

        Values outside the waypoint range are held at the nearest endpoint.
        Between waypoints, the left waypoint's ``after`` and the right
        waypoint's ``before`` settings control the segment.
        """
        return self._at(tosec(time), set())

    def _at(self, time: float, seen: set[int]) -> Value:
        if id(self) in seen:
            raise ValueError("cyclic Animated reference while evaluating animation")
        seen.add(id(self))
        try:
            waypoints = self._ordered_waypoints()
            if not waypoints:
                raise ValueError("cannot evaluate an animation with no waypoints")

            # Validate direct edits to the public waypoint list as well.
            for waypoint in waypoints:
                self._check_waypoint(waypoint)
                if "time" not in waypoint.__dict__:
                    raise ValueError("animation contains a waypoint with no time")
                if "value" not in waypoint.__dict__:
                    raise ValueError(
                        f"animation contains a waypoint with no value "
                        f"(time={waypoint.time!r}s)"
                    )

            times = [wp.time for wp in waypoints]
            from bisect import bisect_right

            right_index = bisect_right(times, time)
            if right_index == 0:
                return self._resolve_waypoint(waypoints[0], time, seen)
            left = waypoints[right_index - 1]
            if right_index == len(waypoints) or time == left.time:
                return self._resolve_waypoint(left, time, seen)
            right = waypoints[right_index]
            if right.time <= left.time:
                return self._resolve_waypoint(left, time, seen)

            start = self._resolve_waypoint(left, time, seen)
            end = self._resolve_waypoint(right, time, seen)
            duration = right.time - left.time
            amount = (time - left.time) / duration

            global_mode = self.__dict__.get("interpolation")
            before = global_mode or right.__dict__.get("before", "auto")
            after = global_mode or left.__dict__.get("after", "auto")
            if "constant" in (before, after):
                return start

            # Synfig's Boolean interpolator is discrete, independent of the
            # waypoint interpolation mode. Other discrete kinds use the Kind
            # implementation's endpoint-switch behavior.
            # Temporal tension changes the time parameterization. Invert the
            # cubic time curve with bisection, as Synfig does for Hermite paths.
            tt0 = left.__dict__.get("temporal_tension", 0.0)
            tt1 = right.__dict__.get("temporal_tension", 0.0)
            if tt0 or tt1:
                target = amount
                lo, hi = 0.0, 1.0
                for _ in range(40):
                    u = (lo + hi) / 2
                    mapped = _hermite(0.0, 1.0, 1.0 - tt0, 1.0 - tt1, u)
                    if mapped < target:
                        lo = u
                    else:
                        hi = u
                amount = (lo + hi) / 2

            if isinstance(start.data, (bool, str)):
                return self.kind.interpolate(start, end, amount)

            if after == "linear" and before == "linear":
                return self.kind.interpolate(start, end, amount)

            # Angles do not use TCB/clamped interpolation in Synfig.
            if self.kind.name == "Angle" and (
                after in ("auto", "clamped") or before in ("auto", "clamped")
            ):
                return self.kind.interpolate(start, end, amount)

            p0, p1 = start.data, end.data
            secant = _sub(p1, p0)
            m0 = secant
            m1 = secant

            if after in ("ease", "halt", "manual"):
                m0 = _scale(secant, 0.0)
            elif after == "auto" and right_index >= 2:
                prev = waypoints[right_index - 2]
                prev_value = self._resolve_waypoint(prev, time, seen).data
                tension = left.__dict__.get("tension", 0.0)
                continuity = left.__dict__.get("continuity", 0.0)
                bias = left.__dict__.get("bias", 0.0)
                d_prev = _sub(p0, prev_value)
                m0 = _add(
                    _scale(d_prev, (1 - tension) * (1 + continuity) * (1 + bias) / 2),
                    _scale(secant, (1 - tension) * (1 - continuity) * (1 - bias) / 2),
                )
                prev_dt = left.time - prev.time
                if prev_dt > 0:
                    m0 = _scale(m0, duration * 1.5 / (duration * 0.5 + prev_dt))
            elif (
                after == "clamped"
                and right_index >= 2
                and waypoints[right_index - 2].time < left.time
            ):
                prev = waypoints[right_index - 2]
                prev_value = self._resolve_waypoint(prev, time, seen).data
                m0 = _clamped_tangent(
                    prev_value, p0, p1, prev.time, left.time, right.time
                )
            elif after == "clamped":
                m0 = secant

            if before in ("ease", "halt", "manual"):
                m1 = _scale(secant, 0.0)
            elif before == "auto" and right_index + 1 < len(waypoints):
                nxt = waypoints[right_index + 1]
                next_value = self._resolve_waypoint(nxt, time, seen).data
                tension = right.__dict__.get("tension", 0.0)
                continuity = right.__dict__.get("continuity", 0.0)
                bias = right.__dict__.get("bias", 0.0)
                d_next = _sub(next_value, p1)
                m1 = _add(
                    _scale(secant, (1 - tension) * (1 - continuity) * (1 + bias) / 2),
                    _scale(d_next, (1 - tension) * (1 + continuity) * (1 - bias) / 2),
                )
                next_dt = nxt.time - right.time
                if next_dt > 0:
                    m1 = _scale(m1, duration * 1.5 / (duration * 0.5 + next_dt))
            elif (
                before == "clamped"
                and right_index + 1 < len(waypoints)
                and waypoints[right_index + 1].time > right.time
            ):
                nxt = waypoints[right_index + 1]
                next_value = self._resolve_waypoint(nxt, time, seen).data
                m1 = _clamped_tangent(
                    p0, p1, next_value, left.time, right.time, nxt.time
                )
            elif before == "clamped":
                m1 = secant

            data = _hermite(p0, p1, m0, m1, amount)
            if isinstance(p0, int) and not isinstance(p0, bool):
                data = int(data + 0.5)
            return self.kind.value_type(data)
        finally:
            seen.remove(id(self))

    def _resolve_waypoint(
        self, waypoint: Waypoint, time: float, seen: set[int]
    ) -> Value:
        value = waypoint.value
        if isinstance(value, Ref):
            target = value.target
            if isinstance(target, str):
                raise ValueError(
                    f"cannot evaluate unresolved reference {target!r}; "
                    "resolve it to a Value or Animated first"
                )
            if isinstance(target, Animated):
                value = target._at(time, seen)
            else:
                value = target
        if not isinstance(value, self.kind.value_type):
            raise ValueError(
                f"waypoint at {waypoint.time!r}s has {type(value).__name__}, "
                f"expected {self.kind.name}"
            )
        return value


# src reference : CanvasParser::parse_animated
