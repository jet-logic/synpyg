from dataclasses import dataclass, field, fields
from typing import Any

from .value import Value
from .valuenode import ValueNode, WithXML


def attr(name="") -> dict[str, Any]:
    return {"attr": {"name": name}}


def parm(name: str, typed: type[Value]) -> dict[str, Any]:
    return {"parm": {"name": name, "typed": typed}}


@dataclass
class Waypoint(WithXML):
    value: Value = field(init=False)
    time: float = field(init=False, metadata={"attr": True})
    before: str = field(init=False, metadata={"attr": True})
    after: str = field(init=False, metadata={"attr": True})
    tension: float = field(init=False, metadata={"attr": True})
    temporal_tension: float = field(init=False, metadata=attr("temporal-tension"))
    continuity: float = field(init=False, metadata={"attr": True})
    bias: float = field(init=False, metadata={"attr": True})

    def set_params(self, **kwargs):
        def _set(k, v):
            for f in fields(self):
                if k == f.name and f.metadata.get("attr"):
                    return setattr(self, k, v)
            raise NameError(f"Unknow params {k}?")

        for k, v in kwargs.items():
            _set(k, v)
        return self

    def to_xml_element(self):
        element = self._etree.Element("waypoint")
        for f in fields(self):
            if m := f.metadata.get("attr"):
                k = a = f.name
                v = self.__dict__.get(k)
                if v is not None:
                    if isinstance(m, dict):
                        if x := m.get("name"):
                            a = x
                    if k == "time":
                        element.set(a, f"{v}s")
                    else:
                        element.set(a, str(v))
        try:
            v = self.value
        except AttributeError:
            pass
        else:
            element.append(v.to_xml_element())
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
