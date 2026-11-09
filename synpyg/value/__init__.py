from typing import Any, Optional, Self
import xml.etree.ElementTree as ET


class Value:
    # Synfig value
    tag = ""
    id: Optional[str]
    guid: Optional[str]

    def __init__(self, id=None, guid=None) -> None:
        self.id = None
        self.guid = None

    def check_value(self, value: Any) -> Self:
        return NotImplementedError()  # type: ignore

    def to_xml_element(self) -> ET.Element:
        raise NotImplementedError


class Scalar(Value):
    value: Any

    def __repr__(self) -> str:
        extras = ""
        if self.id is not None:
            extras += f", id={self.id!r}"
        if self.guid is not None:
            extras += f", guid={self.guid!r}"
        return f"{self.__class__.__name__}({self.value!r}{extras})"

    # def to_xml_element(self):
    #     return ET.Element(
    #         self.tag,
    #         {
    #             "value": (
    #                 str(self.value).lower()
    #                 if isinstance(self.value, bool)
    #                 else str(self.value)
    #             )
    #         },
    #     )


class Real(Scalar):
    # Synfig real value
    value: float
    tag = "real"

    def __init__(self, value: float, **kwargs) -> None:
        super().__init__(**kwargs)
        self.value = value

    def to_xml_element(self):
        return ET.Element("real", {"value": str(self.value)})


class Integer(Scalar):
    value: int
    tag = "integer"

    def __init__(self, value: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.value = value

    def to_xml_element(self):
        return ET.Element("integer", {"value": str(self.value)})


class Boolean(Scalar):
    value: bool
    tag = "bool"

    def __init__(self, value=False, **kwargs):
        super().__init__(**kwargs)
        self.value = value

    def check_value(self, value):
        if isinstance(value, bool):
            return Boolean(value)
        raise ValueError(f"Unexpected boolean {value}")

    def to_xml_element(self):
        return ET.Element("bool", {"value": str(self.value).lower()})


class String(Scalar):
    value: str
    tag = "string"

    def to_xml_element(self):
        return ET.Element("string", {"value": self.value})


class Angle(Scalar):
    value: float
    tag = "angle"

    def to_xml_element(self):
        return ET.Element("angle", {"value": str(self.value)})


class Time(Scalar):
    value: str
    tag = "time"

    def to_xml_element(self):
        return ET.Element("time", {"value": self.value})


class Color(Value):
    r: float
    g: float
    b: float
    a: float = 1.0
    tag = "color"

    def __init__(
        self, r: float = 0.5, g: float = 0.5, b: float = 0.5, a: float = 1.0, **kwargs
    ):
        super().__init__(**kwargs)
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    def __repr__(self) -> str:
        extras = ""
        if self.id is not None:
            extras += f", id={self.id!r}"
        if self.guid is not None:
            extras += f", guid={self.guid!r}"
        return f"{self.__class__.__name__}({(self.r,self.b,self.g,self.a)!r}{extras})"

    def check_value(self, value: Any):
        if isinstance(value, (list, tuple)):
            return Color(*value)
        raise ValueError(f"Unexpected color {value}")

    def to_xml_element(self):
        element = ET.Element("color")

        for channel in ("r", "g", "b", "a"):
            ET.SubElement(element, channel).text = str(getattr(self, channel))

        return element


class Vector(Value):
    x: float
    y: float
    tag = "vector"

    def __init__(self, x=0.0, y=0.0, **kwargs):
        super().__init__(**kwargs)
        self.x = x
        self.y = y

    def check_value(self, value):
        if isinstance(value, (list, tuple)) and len(value) == 2:
            return Vector(*value)
        raise ValueError(f"Unexpected vector {value}")

    def to_xml_element(self):
        element = ET.Element("vector")
        ET.SubElement(element, "x").text = str(self.x)
        ET.SubElement(element, "y").text = str(self.y)
        return element
