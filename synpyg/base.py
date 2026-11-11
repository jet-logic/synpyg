from typing import Any, Callable, Generator, Generic, TypeVar

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

    # def __init__(self, value: Value | Animated | None, name=""):
    #     # if value:
    #     #     self.value = value
    #     self.value = value
    #     self._name = name

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
    _name: str
    # _argv: tuple | object
    value: Value | Animated | None

    def to_xml_element(self):
        element = self._etree.Element("param", {"name": self._name})
        if v := self.value:
            element.append(v.to_xml_element())
        return element


class PreProp(Property):
    # subclassed Property so VS Code will not complain
    def __init__(self, name: str, typed: type[Value]):
        self.name = name
        self.typed = typed

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name!r})"


def paramls(inst: object) -> Generator[list[tuple[str, PreProp]], Any, None]:
    for c in inst.__class__.__mro__:
        try:
            f: list[tuple[str, PreProp]] = c._params  # type: ignore
        except AttributeError:
            pass
        else:
            assert isinstance(f, list)
            yield f


def params(inst: object) -> Generator[tuple[str, PreProp], Any, None]:
    for v in paramls(inst):
        yield from v


_T = TypeVar("_T")


class Pro(Generic[_T]):
    pass


def param(name, typed: type[Value]):
    return PreProp(name, typed)


def param2(cls, name, typed: type[Value]):
    return PreProp(name, typed)
    # return 5# PreProp(name, typed)


class TestXML(WithXML):
    pass
