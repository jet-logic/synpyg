from .attrs import FloatAttr, StringAttr, StringEnumAttr, TimeAttr
from .timeutil import tosec
from .value import Value, ValueKind
from .base import WithFields, WithXML

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
    value: Value  # child element, not an XML attribute, so not a Field
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
        element = et.Element("waypoint", self._xml_attrs())
        element.append(value.to_xml_element(et))
        return element


class Animated(WithFields):
    kind: ValueKind

    id = StringAttr()
    guid = StringAttr()
    interpolation = StringEnumAttr(choices=VALID_INTERPOLATIONS)

    def __init__(
        self,
        kind: ValueKind | type[Value],
        *,
        id=None,
        guid=None,
        interpolation=None,
    ):
        super().__init__()

        kind = ValueKind.of(kind)
        if not kind.tag:
            raise NotImplementedError(f"{kind.name} has no tag and cannot be animated")

        self.kind = kind
        self.waypoints = []

        self._assign_given(id=id, guid=guid, interpolation=interpolation)

    def to_xml_element(self, et):
        attrs = {"type": self.kind.tag, **self._xml_attrs()}
        element = et.Element("animated", attrs)

        for child in self._ordered_waypoints():
            element.append(child.to_xml_element(et))

        return element

    def add_waypoint(self, time, value, *, fps: float | None = None, **kwargs):
        """Add a waypoint. ``time`` may be seconds or a time string; frames
        ("12f") need ``fps``."""
        w = Waypoint()
        w.time = tosec(time, fps)
        w.value = self.kind.coerce(value)
        w._assign(**kwargs)
        self.waypoints.append(w)
        return self

    def _ordered_waypoints(self) -> list[Waypoint]:
        return sorted(self.waypoints, key=lambda w: w.time)  # stable


# src reference : CanvasParser::parse_animated
