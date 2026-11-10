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


class Vec(Value):
    value: tuple[float]

    def __init__(self, value: tuple[float], **kwargs) -> None:
        super().__init__(**kwargs)
        self.value = value

    def __repr__(self) -> str:
        extras = ""
        if self.id is not None:
            extras += f", id={self.id!r}"
        if self.guid is not None:
            extras += f", guid={self.guid!r}"
        return f"{self.__class__.__name__}({self.value!r}{extras})"

    def check_value(self, value: Any):
        if isinstance(value, list):
            return self.__class__(tuple(value))
        if isinstance(value, tuple):
            return self.__class__(value)
        raise ValueError(f"Unexpected vector {value}")


class Color(Vec):
    tag = "color"

    def __init__(self, value, **kwargs):
        assert len(value) == 4
        super().__init__(value, **kwargs)

    def to_xml_element(self):
        element = ET.Element("color")

        for channel, n in zip(("r", "g", "b", "a"), self.value):
            ET.SubElement(element, channel).text = str(n)

        return element


class Vector(Vec):
    tag = "vector"

    def __init__(self, value, **kwargs):
        assert len(value) == 2
        super().__init__(value, **kwargs)

    def to_xml_element(self):
        element = ET.Element("vector")
        for s, n in zip(("x", "y"), self.value):
            ET.SubElement(element, s).text = str(n)
        return element
