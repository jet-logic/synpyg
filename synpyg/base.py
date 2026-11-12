from dataclasses import field
from typing import Any, Callable, TYPE_CHECKING
from .valuenode import WithXML
from .value import Value
from .tree.linked3 import Node

if TYPE_CHECKING:
    from .animated import Animated

# node_dataclass = partial(dataclass, eq=False, kw_only=True, init=False)


class Base(Node):
    pass


class Property(WithXML):
    """
    A Synfig param
    """

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__dict__.get('value')!r})"

    def set_value(self, value: Any):
        self.value = self.typed.check_value(value)

    def as_animated(self):
        try:
            if isinstance(self.value, Animated):
                return self.value
        except AttributeError:
            pass
        v = self.value = self.typed.new_animated()
        return v

    typed: type[Value]
    name: str
    value: "Value | Animated | None"

    def to_xml_element(self):
        element = self._etree.Element("param", {"name": self.name})
        if v := self.value:
            element.append(v.to_xml_element())
        return element


def param(name, typed: type[Value]):
    return field(init=False, metadata={"parm": {"name": name, "typed": typed}})


def attr(name="", strf: Callable[[object], str] = str):
    return field(init=False, metadata={"attr": {"name": name, "strf": strf}})
