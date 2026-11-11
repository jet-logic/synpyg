from typing import Any, Callable, Generator

from .valuenode import WithXML
from .animated import Animated
from .value import Value
from .tree.linked3 import Node


class Base(Node):
    pass


class Property(WithXML):
    """
    A Synfig param
    """

    def __init__(self, value: Value | Animated | None, name=""):
        # if value:
        #     self.value = value
        self.value = value
        self._name = name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value!r})"

    def set_value(self, value: Any):
        self.value = self._type.check_value(value)

    def as_animated(self):
        if isinstance(self.value, Animated):
            return self.value
        v = self.value = self._type.new_animated()
        return v

    _type: type[Value]
    _name: str
    _argv: tuple | object
    value: Value | Animated | None

    # def __getattr__(self, name):
    #     if not name.startswith("_get_"):
    #         f = getattr(self, f"_get_{name}", None)
    #         if f:
    #             v = f()
    #             setattr(self, name, v)
    #             return v

    # def _get_value(self):
    #     p = self._type
    #     a = self._argv
    #     if a is None:
    #         v = p()
    #     elif isinstance(a, tuple):
    #         v = p(*a)
    #     else:
    #         v = p(a)
    #     # print("FIELD", name, v, v.__class__.__name__)
    #     return v

    def to_xml_element(self):
        element = self._etree.Element("param", {"name": self._name})
        if v := self.value:
            element.append(v.to_xml_element())
        return element


class Field(Property):
    # subclassed Property so VS Code will not complain
    def __init__(
        self, name: str, producer: type[Value], argv: tuple | object, **kwargs
    ):
        self.name = name
        self.type = producer
        self.argv = argv

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name!r})"


def paramls(inst: object) -> Generator[list[tuple[str, Field]], Any, None]:
    for c in inst.__class__.__mro__:
        try:
            f: list[tuple[str, Field]] = c._params  # type: ignore
        except AttributeError:
            pass
        else:
            assert isinstance(f, list)
            yield f


def params(inst: object) -> Generator[tuple[str, Field], Any, None]:
    for v in paramls(inst):
        yield from v


def param(name: str = "", producer=Callable[..., Any], argv: tuple | object = ()):
    return Field(name, producer, argv)


class TestXML(WithXML):
    pass
