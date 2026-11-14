from typing import TYPE_CHECKING, Any, Optional, Self
from synpyg.numeric import to_float, to_float_tuple, to_int
from synpyg.numfmt import fmt_num
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

    def _xml_attrs(self):
        return {"guid": self.guid} if self.guid is not None else {}

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
    tag = "real"

    def __init__(self, data: float, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = to_float(data, name=type(self).__name__)

    @classmethod
    def check_value(cls, value: Any) -> Self:
        return cls(value)

    def to_xml_element(self, et):
        return et.Element(self.tag, {"value": fmt_num(self.data), **self._xml_attrs()})


class Integer(Const):
    tag = "integer"

    def __init__(self, data: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = to_int(data, name=type(self).__name__)

    @classmethod
    def check_value(cls, value: Any) -> Self:
        return cls(value)

    def to_xml_element(self, et):
        return et.Element(self.tag, {"value": str(self.data)}, **self._xml_attrs())


class Boolean(Const):
    tag = "bool"

    def __init__(self, data: bool = False, **kwargs):
        super().__init__(**kwargs)
        if not isinstance(data, bool):
            raise ValueError(f"Unexpected {type(self).__name__} value: {data!r}")
        self.data = data

    @classmethod
    def check_value(cls, value):
        return cls(value)

    def to_xml_element(self, et):
        return et.Element(
            self.tag, {"value": "true" if self.data else "false"}, **self._xml_attrs()
        )


class String(Const):
    tag = "string"

    def __init__(self, data: str, **kwargs) -> None:
        super().__init__(**kwargs)
        if not isinstance(data, str):
            raise ValueError(f"Unexpected {type(self).__name__} value: {data!r}")
        self.data = data

    @classmethod
    def check_value(cls, value: Any) -> Self:
        return cls(value)

    def to_xml_element(self, et):
        return et.Element(self.tag, {"value": self.data}, **self._xml_attrs())


class Angle(Const):
    tag = "angle"

    def __init__(self, data: float, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = to_float(data, name=type(self).__name__)

    @classmethod
    def check_value(cls, value: Any) -> Self:
        return cls(value)

    def to_xml_element(self, et):
        return et.Element(self.tag, {"value": fmt_num(self.data)}, **self._xml_attrs())


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
        return et.Element(self.tag, {"value": fmt_time(self.data)}, **self._xml_attrs())


class Vec(Const):
    data: tuple[float, ...]

    def __init__(self, data, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = to_float_tuple(
            data,
            name=type(self).__name__,
        )

    @classmethod
    def check_value(cls, value: Any):
        if isinstance(value, (str, bytes, bytearray)):
            raise ValueError(f"Unexpected {cls.__name__} {value!r}")

        try:
            iter(value)
        except TypeError:
            raise ValueError(f"Unexpected {cls.__name__} {value!r}") from None

        return cls(value)


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
        element = et.Element(self.tag, self._xml_attrs())
        for channel, n in zip(("r", "g", "b", "a"), self.data):
            et.SubElement(element, channel).text = fmt_num(n)
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
        element = et.Element(self.tag, self._xml_attrs())
        for s, n in zip(("x", "y"), self.data):
            et.SubElement(element, s).text = fmt_num(n)
        return element
