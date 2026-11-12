from .base import Attr, WithAttrs
from .value import Value, timef, timep
from .base import WithXML


class Waypoint(WithAttrs, WithXML):
    """
    A Synfig Waypoint
    """

    # NOTE: member validation is done by Animated class
    #       Waypoint should remain a lightweight data and serialization class
    # TODO: use attribute
    value: Value
    time = Attr(strf=lambda v: timef(timep(v)))
    before = Attr()
    after = Attr()
    temporal_tension = Attr("temporal-tension")
    continuity = Attr()
    bias = Attr()

    def to_xml_element(self, et):
        try:
            value = self.value
        except AttributeError:
            at = self.__dict__.get("time")
            raise ValueError(
                "Waypoint has no value" + (f" (time={at!r})" if at is not None else "")
            ) from None
        element = et.Element("waypoint")
        for key, a in self._attrs.items():
            v = self.__dict__.get(key)
            if v is not None:
                assert a.name
                element.set(a.name, a.strf(v))
        element.append(value.to_xml_element(et))
        return element


# can waypoint have a value node or just const value


class Animated:
    _type: type[Value]
    interpolation: str | None = None
    node_id: str | None = None

    def __init__(self) -> None:
        super().__init__()
        self.waypoints: list[Waypoint] = []

    def add_waypoint(self, time, value, **kwargs):
        timef(timep(time))  # fail now on a bad time, not when saving
        w = Waypoint()
        w.time = time
        w.value = self._type.coerce(value)
        w.set_params(**kwargs)
        self.waypoints.append(w)
        return self

    def _ordered_waypoints(self) -> list[Waypoint]:
        """
        Waypoints sorted by time (stable, so equal times keep insertion order).

        Frame offsets can't be compared with seconds without the canvas fps, so if
        any waypoint uses frames (or has no time) insertion order is kept as is.
        """
        times = [w.__dict__.get("time") for w in self.waypoints]
        if any(t is None for t in times):
            return list(self.waypoints)
        parsed = [timep(t) for t in times]
        if any(t.imag != 0 for t in parsed):
            return list(self.waypoints)
        order = sorted(range(len(parsed)), key=lambda i: parsed[i].real)
        return [self.waypoints[i] for i in order]

    def to_xml_element(self, et):
        element = et.Element("animated", {"type": self._type.tag})
        # TODO: interpolation
        for child in self._ordered_waypoints():
            element.append(child.to_xml_element(et))
        return element


# src reference : CanvasParser::parse_animated
