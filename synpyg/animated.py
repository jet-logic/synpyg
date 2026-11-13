from .field import FloatAttr, StringEnumAttr, TimeAttr
from .timeutil import tosec
from .value import Value
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


class Animated:
    _type: type[Value]
    interpolation: str | None = None
    node_id: str | None = None

    def __init__(self) -> None:
        super().__init__()
        self.waypoints: list[Waypoint] = []

    def add_waypoint(self, time, value, *, fps: float | None = None, **kwargs):
        """Add a waypoint. ``time`` may be seconds or a time string; frames
        ("12f") need ``fps``."""
        w = Waypoint()
        w.time = tosec(time, fps)
        w.value = self._type.coerce(value)
        w._assign(**kwargs)
        self.waypoints.append(w)
        return self

    def _ordered_waypoints(self) -> list[Waypoint]:
        return sorted(self.waypoints, key=lambda w: w.time)  # stable

    def to_xml_element(self, et):
        element = et.Element("animated", {"type": self._type.tag})
        # TODO: interpolation

        for child in self._ordered_waypoints():
            element.append(child.to_xml_element(et))
        return element


# src reference : CanvasParser::parse_animated
