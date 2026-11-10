from typing import Any, Callable, Generator
from .value import Value
from .tree.linked3 import Node


class Base(Node):
    pass


class Property:
    """
    A Synfig param
    """

    def __init__(self, value: Value):
        self.value = value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value!r})"

    def set_value(self, value: Any):
        self.value = self.value.check_value(value)


class Field(Property):
    # subclassed Property so VS Code will not complain
    def __init__(
        self, name: str, producer: Callable[..., Any], argv: tuple | object, **kwargs
    ):
        self.name = name
        self.producer = producer
        self.argv = argv

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name!r})"


def params(inst: object) -> Generator[tuple[str, Field, object], Any, None]:
    for c in inst.__class__.__mro__:
        try:
            f: list[tuple[str, Field, object]] = c._params  # type: ignore
        except AttributeError:
            pass
        else:
            assert isinstance(f, list)
            yield from f


def param(name: str = "", producer=Callable[..., Any], argv: tuple | object = ()):
    return Field(name, producer, argv)
