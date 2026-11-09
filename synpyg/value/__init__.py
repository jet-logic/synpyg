from typing import Any, Optional


class Value:
    # Synfig value
    tag = ""
    id: Optional[str]
    guid: Optional[str]

    def __init__(self, id=None, guid=None) -> None:
        self.id = None
        self.guid = None


class Scalar(Value):
    value: Any

    def __repr__(self) -> str:
        extras = ""
        if self.id is not None:
            extras += f", id={self.id!r}"
        if self.guid is not None:
            extras += f", guid={self.guid!r}"
        return f"{self.__class__.__name__}({self.value!r}{extras})"


class Real(Scalar):
    # Synfig real value
    value: float
    tag = "real"

    def __init__(self, value: float, **kwargs) -> None:
        super().__init__(**kwargs)
        self.value = value


class Integer(Scalar):
    value: int
    tag = "integer"

    def __init__(self, value: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.value = value

    def __repr__(self) -> str:
        extras = ""
        if self.id is not None:
            extras += f", id={self.id!r}"
        if self.guid is not None:
            extras += f", guid={self.guid!r}"
        return f"{self.__class__.__name__}({self.value!r}{extras})"


class Boolean(Scalar):
    value: bool
    tag = "bool"

    def __init__(self, value: bool, **kwargs) -> None:
        super().__init__(**kwargs)
        self.value = value


class String(Scalar):
    value: str
    tag = "string"


class Angle(Scalar):
    value: float
    tag = "angle"


class Time(Scalar):
    value: str
    tag = "time"


class Vector(Value):
    x: float
    y: float
    tag = "vector"


class Color(Value):
    r: float
    g: float
    b: float
    a: float = 1.0
    tag = "color"
