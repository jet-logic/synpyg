from .base import Attr, WithAttrs
from .value import Value
from .valuenode import ValueNode, WithXML


class Waypoint(WithAttrs, WithXML):
    value: Value
    time = Attr(strf=(lambda v: f"{v}s"))
    before = Attr()
    after = Attr()
    tension = Attr()
    temporal_tension = Attr("temporal-tension")
    continuity = Attr()
    bias = Attr()

    def to_xml_element(self):
        element = self._etree.Element("waypoint")
        for key, a in self._attrs.items():
            v = self.__dict__.get(key)
            if v is not None:
                assert a.name
                element.set(a.name, a.strf(v))
        try:
            value = self.value
        except AttributeError:
            pass
        else:
            element.append(value.to_xml_element())
        return element


# can waypoint have a value node or just const value


class Animated(ValueNode):
    _type: type[Value]
    interpolation: str | None = None
    node_id: str | None = None

    def __init__(self) -> None:
        super().__init__()
        self.waypoints: list[Waypoint] = []

    def add_waypoint(self, time, value, **kwargs):
        w = Waypoint()
        w.time = time
        w.value = value
        w.set_params(**kwargs)
        self.waypoints.append(w)
        return self

    def to_xml_element(self):
        element = self._etree.Element("animated", {"type": self._type.tag})
        # TODO: interpolation
        for child in self.waypoints:
            element.append(child.to_xml_element())
        return element


# src reference : CanvasParser::parse_animated
