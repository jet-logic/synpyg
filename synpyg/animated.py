import math

from .attrs import FloatAttr, StringAttr, StringEnumAttr, TimeAttr
from .ref import Ref
from .timeutil import tosec
from .value import Value, ValueKind
from .base import WithFields, WithXML

# Times closer than this are the same instant: 0.1 + 0.2 and 0.3 differ by
# float noise only. Well below any frame duration, well above float error.
_TIME_ABS_TOL = 1e-9
_TIME_REL_TOL = 1e-12


def _same_time(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=_TIME_REL_TOL, abs_tol=_TIME_ABS_TOL)


VALID_INTERPOLATIONS = (
    "auto",
    "clamped",
    "constant",
    "ease",
    "halt",
    "linear",
    "manual",
)


class Waypoint(WithFields, WithXML):
    # users are expected to use Animated.add_waypoint,
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
        """Validate a waypoint that may have bypassed ``add_waypoint``."""
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

    def add_waypoint(
        self,
        time,
        value,
        *,
        add=False,
        start: float | None = None,  # TODO
        fps: float | None = None,
        **kwargs,
    ):
        """Add a waypoint. ``time`` may be seconds or a time string; frames
        ("12f") need ``fps``."""
        w = Waypoint()
        w.time = t = tosec(time, fps)
        w.value = v = self.kind.coerce(value)
        self._reject_self_reference(v)
        w._assign_given(**kwargs)  # None leaves a field unset, as in Animated(...)

        # A To() action supplies its start time as well as its end time. Add a
        # waypoint carrying the value already in effect at that start, so the
        # interpolation begins there rather than at an earlier keyframe.
        hold = None
        if start is not None:
            start = tosec(start, fps)
            if start > t and not _same_time(start, t):
                raise ValueError(
                    f"start time {start!r}s is after waypoint time {t!r}s"
                )
            if not _same_time(start, t) and self.waypoints:
                at_start = [
                    wp
                    for wp in self.waypoints
                    if wp.time <= start or _same_time(wp.time, start)
                ]
                if at_start and not any(
                    _same_time(wp.time, start) for wp in self.waypoints
                ):
                    previous = max(reversed(at_start), key=lambda wp: wp.time)
                    hold = Waypoint()
                    hold.time = start
                    hold.value = previous.value

        if add:
            if not self.waypoints:
                raise ValueError("No previous waypoint")
            # The previous waypoint is the latest in time (the last one
            # inserted, among equal times), not simply the last one inserted.
            last = max(reversed(self.waypoints), key=lambda wp: wp.time)
            same = _same_time(t, last.time)
            if t < last.time and not same:
                raise ValueError(
                    f"time must be incremental: {t!r}s is before the "
                    f"previous waypoint at {last.time!r}s"
                )
            w.value = v = self.kind.add(last.value, v)
            if same:
                if hold is not None:
                    self.waypoints.append(hold)
                last.value = v
                last._assign_given(**kwargs)
                return self
        if hold is not None:
            self.waypoints.append(hold)
        self.waypoints.append(w)
        return self

    def _ordered_waypoints(self) -> list[Waypoint]:
        return sorted(self.waypoints, key=lambda w: w.time)  # stable


# src reference : CanvasParser::parse_animated
