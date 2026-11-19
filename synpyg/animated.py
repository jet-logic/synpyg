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
        start: float | str | None = None,
        fps: float | None = None,
        **kwargs,
    ):
        """Add a waypoint. ``time`` may be seconds or a time string; frames
        ("12f") need ``fps``. Times are always finite floats.

        ``start`` is the time an interpolation towards this waypoint begins
        (supplied by the ``To`` action). If no waypoint sits at ``start``, a
        hold waypoint is inserted there carrying the value of the latest
        waypoint before it, so the move starts at ``start`` instead of at an
        earlier keyframe. Note this is that waypoint's own value, not the
        interpolated value, which differs when later waypoints exist."""
        w = Waypoint()
        w.time = t = tosec(time, fps)
        w.value = v = self.kind.coerce(value)
        self._reject_self_reference(v)
        w._assign_given(**kwargs)  # None leaves a field unset, as in Animated(...)

        hold = None
        if start is not None:
            start = tosec(start, fps)
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


# src reference : CanvasParser::parse_animated
