from typing import TYPE_CHECKING, Any, Optional, Self, Union


from ..valuenode import WithXML

if TYPE_CHECKING:
    from ..animated import Animated


class Value(WithXML):
    # Synfig value
    tag = ""
    id: Optional[str]
    guid: Optional[str]
    data: Any

    # loop?
    # static?
    # interpolation?

    def __init__(self, id=None, guid=None) -> None:
        self.id = None
        self.guid = None

    @classmethod
    def check_value(cls, value: Any) -> Self:
        raise NotImplementedError(f"{cls.__name__}")

    @classmethod
    def new_animated(cls) -> "Animated":
        raise NotImplementedError(f"{cls.__name__}")

    def as_prop(self, name=""):
        from ..base import Property

        p = Property()
        p.value = self
        p._name = name
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

    def to_xml_element(self):
        return self._etree.Element("real", {"value": str(self.data)})

    @classmethod
    def check_value(cls, value: Any) -> Self:
        if isinstance(value, (bool, str, int, float)):
            return cls(float(value))
        raise ValueError(f"Unexpected boolean {value}")


class Integer(Const):
    data: int
    tag = "integer"

    def __init__(self, data: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = data

    def to_xml_element(self):
        return self._etree.Element("integer", {"value": str(self.data)})

    @classmethod
    def check_value(cls, value: Any) -> Self:
        if isinstance(value, (bool, str, int, float)):
            return cls(int(value))
        raise ValueError(f"Unexpected boolean {value}")


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
        raise ValueError(f"Unexpected boolean {value}")

    def to_xml_element(self):
        return self._etree.Element("bool", {"value": str(self.data).lower()})


class String(Const):
    data: str
    tag = "string"

    def to_xml_element(self):
        return self._etree.Element("string", {"value": self.data})


class Angle(Const):
    data: float
    tag = "angle"

    def to_xml_element(self):
        return self._etree.Element("angle", {"value": str(self.data)})


class Time(Const):
    data: complex
    tag = "time"

    def __init__(self, data, **kwargs):
        super().__init__(**kwargs)
        self.data = data

    @classmethod
    def check_value(cls, value):
        return Time(timep(value))

    def to_xml_element(self):
        return self._etree.Element("time", {"value": timef(self.data)})


class Vec(Const):
    data: tuple[float, ...]

    def __init__(self, data: tuple[float, ...] | list[float], **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = tuple(data)

    @classmethod
    def check_value(cls, value: Any):
        if isinstance(value, (list, tuple)):
            return cls(value)
        raise ValueError(f"Unexpected {cls.__name__} {value!r}")


class Color(Vec):
    tag = "color"

    def __init__(self, data, **kwargs):
        assert len(data) == 4
        super().__init__(data, **kwargs)

    def to_xml_element(self):
        element = self._etree.Element("color")
        for channel, n in zip(("r", "g", "b", "a"), self.data):
            self._etree.SubElement(element, channel).text = str(n)
        return element


class Vector(Vec):
    tag = "vector"

    def __init__(self, data, **kwargs):
        assert len(data) == 2
        super().__init__(data, **kwargs)

    def to_xml_element(self):
        element = self._etree.Element("vector")
        for s, n in zip(("x", "y"), self.data):
            self._etree.SubElement(element, s).text = str(n)
        return element

    @classmethod
    def new_animated(cls) -> "Animated":
        from ..animated import Animated

        a = Animated()
        a._type = cls
        return a


def timep(s: Union[str, float, int, complex]) -> complex:
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
