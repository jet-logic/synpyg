from typing import TYPE_CHECKING, Any, Optional, Self, Union


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
        return f"{self.__class__.__name__}({self.data!r}{extras})"


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
    data: complex
    tag = "time"

    def __init__(self, data, **kwargs):
        super().__init__(**kwargs)
        self.data = data

    @classmethod
    def check_value(cls, value):
        return Time(timep(value))

    def to_xml_element(self, et):
        return et.Element("time", {"value": timef(self.data)})


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


def timep(s: Union[str, float, int, complex, object]) -> complex:
    if isinstance(s, str):
        s = s.strip()
        if ":" in s:
            parts = [float(p) for p in s.lstrip(":").rsplit(":", 2)]
            total = parts.pop()
            if parts:
                total += parts.pop() * 60
            if parts:
                total += parts.pop() * 3600
            return complex(total)
        elif s.endswith("ms"):
            return complex(float(s[:-2]) / 1000)
        elif s.endswith("s"):
            return complex(float(s[:-1]))
        elif s.endswith("f"):
            return complex(0, float(s[:-1]))  # frames in imaginary part
        else:
            return complex(float(s))  # plain number string
    elif isinstance(s, (float, int)):
        return complex(float(s))
    elif isinstance(s, complex):
        return s
    raise ValueError(f"Invalid time {s!r}")


def timef(v: complex) -> str:
    """Format synfig time.

    .real = time in seconds (serialized with 's' suffix)
    .imag = frame offset    (serialized with 'f' suffix)
    """
    secs = v.real
    frames = v.imag

    # Normalize -0.0 and ints that are whole numbers
    def _fmt_secs(x: float) -> str:
        if x == int(x):
            return str(int(x))
        # repr gives shortest round-trip form; strip a trailing '.0'
        return repr(x)

    def _fmt_frames(x: float) -> str:
        # frames are logically integers; require them to be whole
        if x != int(x):
            raise ValueError(f"frame count must be integral, got {x!r}")
        return str(int(x))

    has_secs = secs != 0
    has_frames = frames != 0

    if not has_secs and not has_frames:
        return "0s"

    parts = []
    if has_secs:
        parts.append(_fmt_secs(secs) + "s")
    if has_frames:
        parts.append(_fmt_frames(frames) + "f")

    return " ".join(parts)
