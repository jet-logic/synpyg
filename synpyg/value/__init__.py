from typing import TYPE_CHECKING, Any, Optional, Self, Union


class Value:
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

    def check_value(self, value: Any) -> Self:
        raise NotImplementedError(f"{self.__class__.__name__}")

    def to_xml_element(self) -> "ET.Element":
        raise NotImplementedError(f"{self.__class__.__name__}")

    def __repr__(self) -> str:
        extras = ""
        if self.id is not None:
            extras += f", id={self.id!r}"
        if self.guid is not None:
            extras += f", guid={self.guid!r}"
        return f"{self.__class__.__name__}({self.data!r}{extras})"


class Real(Value):
    # Synfig real value
    data: float
    tag = "real"

    def __init__(self, data: float, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = data

    def to_xml_element(self):
        return ET.Element("real", {"value": str(self.data)})

    def check_value(self, value: Any) -> Self:
        if isinstance(value, (bool, str, int, float)):
            return self.__class__(float(value))
        raise ValueError(f"Unexpected boolean {value}")


class Integer(Value):
    data: int
    tag = "integer"

    def __init__(self, data: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = data

    def to_xml_element(self):
        return ET.Element("integer", {"value": str(self.data)})

    def check_value(self, value: Any) -> Self:
        if isinstance(value, (bool, str, int, float)):
            return self.__class__(int(value))
        raise ValueError(f"Unexpected boolean {value}")


class Boolean(Value):
    data: bool
    tag = "bool"

    def __init__(self, data=False, **kwargs):
        super().__init__(**kwargs)
        self.data = data

    def check_value(self, value):
        if isinstance(value, bool):
            return Boolean(value)
        raise ValueError(f"Unexpected boolean {value}")

    def to_xml_element(self):
        return ET.Element("bool", {"value": str(self.data).lower()})


class String(Value):
    data: str
    tag = "string"

    def to_xml_element(self):
        return ET.Element("string", {"value": self.data})


class Angle(Value):
    data: float
    tag = "angle"

    def to_xml_element(self):
        return ET.Element("angle", {"value": str(self.data)})


class Time(Value):
    data: complex
    tag = "time"

    def __init__(self, data, **kwargs):
        super().__init__(**kwargs)
        self.data = data

    def check_value(self, value):
        return Time(timep(value))

    def to_xml_element(self):
        return ET.Element("time", {"value": timef(self.data)})


class Vec(Value):
    data: tuple[float, ...]

    def __init__(self, data: tuple[float, ...], **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = data

    def check_value(self, value: Any):
        if isinstance(value, list):
            return self.__class__(tuple(value))
        elif isinstance(value, tuple):
            return self.__class__(value)
        raise ValueError(f"Unexpected {self.__class__.__name__} {value}")


class Color(Vec):
    tag = "color"

    def __init__(self, data, **kwargs):
        assert len(data) == 4
        super().__init__(data, **kwargs)

    def to_xml_element(self):
        element = ET.Element("color")
        for channel, n in zip(("r", "g", "b", "a"), self.data):
            ET.SubElement(element, channel).text = str(n)
        return element


class Vector(Vec):
    tag = "vector"

    def __init__(self, data, **kwargs):
        assert len(data) == 2
        super().__init__(data, **kwargs)

    def to_xml_element(self):
        element = ET.Element("vector")
        for s, n in zip(("x", "y"), self.data):
            ET.SubElement(element, s).text = str(n)
        return element


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


from xml.etree import ElementTree as ET
