from typing import TYPE_CHECKING, Any, Optional, Self

from synpyg.timeutil import fmt_time, tosec


from .base import WithXML

if TYPE_CHECKING:
    from .animated import Animated


class Value(WithXML):
    # Synfig value
    tag = ""
    id: Optional[str]
    guid: Optional[str]
    data: Any

    # loop?
    # static?
    # interpolation?
    def __init__(self, id: Optional[str] = None, guid: Optional[str] = None) -> None:
        """Initialize optional Synfig value identifiers."""
        self.id = id
        self.guid = guid

    @classmethod
    def check_value(cls, value: Any) -> Self:
        raise NotImplementedError(f"{cls.__name__}")

    @classmethod
    def coerce(cls, value: Any) -> Self:
        """Return ``value`` if it is already a ``cls``, otherwise validate and wrap it."""
        if isinstance(value, cls):
            return value
        return cls.check_value(value)

    @classmethod
    def new_animated(cls) -> "Animated":
        """Create an :class:`Animated` value node that produces values of ``cls``."""
        from .animated import Animated

        if not cls.tag:
            # A non-serializable base class (Value, Const, Vec) — don't hand out
            # an Animated that would fail on ``self._type.tag`` at save time.
            raise NotImplementedError(
                f"{cls.__name__} has no tag and cannot be animated"
            )
        a = Animated()
        a._type = cls
        return a

    def as_prop(self, name=""):
        from .base import Property

        p = Property()
        p.value = self
        p.name = name
        p.typed = self.__class__
        return p

    def __repr__(self) -> str:
        extras = ""
        if self.id is not None:
            extras += f", id={self.id!r}"
        if self.guid is not None:
            extras += f", guid={self.guid!r}"
        return f"{self.__class__.__name__}({self.__dict__.get('data')!r}{extras})"


class Const(Value):
    pass


class Real(Const):
    # Synfig real value
    data: float
    tag = "real"

    def __init__(self, data: float, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = data

    def to_xml_element(self, et):
        return et.Element("real", {"value": str(self.data)})

    @classmethod
    def check_value(cls, value: Any) -> Self:
        if isinstance(value, (bool, str, int, float)):
            return cls(float(value))
        raise ValueError(f"Unexpected {cls.__name__} {value}")


class Integer(Const):
    data: int
    tag = "integer"

    def __init__(self, data: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = data

    def to_xml_element(self, et):
        return et.Element("integer", {"value": str(self.data)})

    @classmethod
    def check_value(cls, value: Any) -> Self:
        if isinstance(value, (str, int, float)):
            return cls(int(value))
        raise ValueError(f"Unexpected {cls.__name__} value: {value}")


class Boolean(Const):
    data: bool
    tag = "bool"

    def __init__(self, data=False, **kwargs):
        super().__init__(**kwargs)
        self.data = data

    @classmethod
    def check_value(cls, value):
        if isinstance(value, bool):
            return Boolean(value)
        raise ValueError(f"Unexpected {cls.__name__} value: {value}")

    def to_xml_element(self, et):
        return et.Element("bool", {"value": str(self.data).lower()})


class String(Const):
    data: str
    tag = "string"

    def __init__(self, data: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = data

    @classmethod
    def check_value(cls, value: Any) -> Self:
        if isinstance(value, str):
            return cls(value)
        raise ValueError(f"Unexpected {cls.__name__} {value!r}")

    def to_xml_element(self, et):
        return et.Element("string", {"value": self.data})


class Angle(Const):
    data: float
    tag = "angle"

    def __init__(self, data: float, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = data + 0.0

    @classmethod
    def check_value(cls, value: Any) -> Self:
        if isinstance(value, (str, int, float)):
            return cls(float(value))
        raise ValueError(f"Unexpected {cls.__name__} {value!r}")

    def to_xml_element(self, et):
        return et.Element("angle", {"value": str(self.data)})


class Time(Const):
    data: float  # seconds
    tag = "time"

    def __init__(self, data, fps: float | None = None, **kwargs):
        """``data`` may be seconds or a time string; frames ("12f") need ``fps``."""
        super().__init__(**kwargs)
        self.data = tosec(data, fps)

    @classmethod
    def check_value(cls, value):
        return cls(value)

    def to_xml_element(self, et):
        return et.Element("time", {"value": fmt_time(self.data)})


class Vec(Const):
    data: tuple[float, ...]

    def __init__(self, data: tuple[float, ...] | list[float], **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = tuple(float(x) for x in data)

    @classmethod
    def check_value(cls, value: Any):
        if isinstance(value, (list, tuple)):
            return cls(value)
        raise ValueError(f"Unexpected {cls.__name__} {value!r}")


class Color(Vec):
    tag = "color"

    def __init__(self, data, **kwargs):
        data = tuple(data)
        if len(data) != 4:
            raise ValueError(
                f"Color needs exactly 4 channels (r, g, b, a), got {len(data)}"
            )
        super().__init__(data, **kwargs)

    def to_xml_element(self, et):
        element = et.Element("color")
        for channel, n in zip(("r", "g", "b", "a"), self.data):
            et.SubElement(element, channel).text = str(n)
        return element


class Vector(Vec):
    tag = "vector"

    def __init__(self, data, **kwargs):
        data = tuple(data)
        if len(data) != 2:
            raise ValueError(
                f"Vector needs exactly 2 components (x, y), got {len(data)}"
            )
        super().__init__(data, **kwargs)

    def to_xml_element(self, et):
        element = et.Element("vector")
        for s, n in zip(("x", "y"), self.data):
            et.SubElement(element, s).text = str(n)
        return element
