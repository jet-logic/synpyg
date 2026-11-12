from functools import cached_property
from typing import TYPE_CHECKING


class WithXML:
    def to_xml_element(self):
        if 1:
            raise NotImplementedError(f"{self.__class__.__name__}")
        return self._etree.Element("??")  # for typing

    @cached_property
    def _etree(self):
        from xml.etree import ElementTree as ET

        return ET

    def etree2(self):
        from xml.etree import ElementTree as ET

        return ET

    # etree: 'Module("xml.etree.ElementTree")'


# from xml.etree import ElementTree as ET


class ValueNode(WithXML):
    pass
