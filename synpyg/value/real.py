import xml.etree.ElementTree as ET
from typing import Optional

from ..base import Base


class RealValue(Base):
    """
    Represents a Synfig 'real' value in a .sif file.

    XML form (constant):
        <real value="1.0000000000"/>

    XML form (exported, inside <defs>):
        <real id="MyExportedReal" value="5.0"/>
    """

    TAG = "real"

    def __init__(
        self,
        value: float,
        id: Optional[str] = None,
        guid: Optional[str] = None,
    ):
        self.value: float = float(value)
        self.id: Optional[str] = id  # exported identifier
        self.guid: Optional[str] = guid  # optional GUID

    # ---------- Parsing ----------

    @classmethod
    def from_xml(cls, elem: ET.Element) -> "RealValue":
        """Build a RealValue from an <real> XML element."""
        if elem.tag != cls.TAG:
            raise ValueError(f"Expected <{cls.TAG}>, got <{elem.tag}>")

        raw = elem.get("value")
        if raw is None:
            raise ValueError("<real> element missing 'value' attribute")

        return cls(
            value=float(raw),  # '.' is the decimal separator in .sif
            id=elem.get("id"),
            guid=elem.get("guid"),
        )

    # ---------- Serialization ----------

    def to_xml(self, precision: int = 10) -> ET.Element:
        """Serialize to an <real> XML element."""
        elem = ET.Element(self.TAG)
        elem.set("value", f"{self.value:.{precision}f}")
        if self.id is not None:
            elem.set("id", self.id)
        if self.guid is not None:
            elem.set("guid", self.guid)
        return elem

    # ---------- Convenience ----------

    def __float__(self) -> float:
        return self.value

    def __repr__(self) -> str:
        extras = ""
        if self.id is not None:
            extras += f", id={self.id!r}"
        if self.guid is not None:
            extras += f", guid={self.guid!r}"
        return f"RealValue({self.value!r}{extras})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, RealValue):
            return NotImplemented
        return (
            self.value == other.value
            and self.id == other.id
            and self.guid == other.guid
        )
