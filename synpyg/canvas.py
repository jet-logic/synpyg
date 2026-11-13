from typing import Any
from .base import WithFields, WithXML
from .field import FloatAttr, IntAttr, StringAttr, TimeAttr
from .layer import Grouping, Layer

from typing import Any, Optional, Sequence
from .field import FloatAttr, IntAttr, QuadFloatAttr, StringAttr, TimeAttr


class Canvas(WithFields, WithXML, Grouping):
    version = StringAttr(required=True)
    width = IntAttr(required=True)
    height = IntAttr(required=True)
    fps = FloatAttr(required=True)
    begin_time = TimeAttr(name="begin-time", fps_attr="fps")
    end_time = TimeAttr(name="end-time", fps_attr="fps")
    view_box = QuadFloatAttr(name="view-box")

    def __init__(
        self,
        version="1.2",
        width=480,
        height=270,
        fps=24.0,
        begin_time=None,
        end_time=None,
        view_box=None,
    ):
        super().__init__()
        self.version = version
        self.width = width
        self.height = height
        self.fps = fps  # before the times, so "12f" can be resolved
        # optional attributes stay unset (and out of the XML) when None
        if begin_time is not None:
            self.begin_time = begin_time
        if end_time is not None:
            self.end_time = end_time
        if view_box is not None:
            self.view_box = view_box
        self.meta: dict[str, Any] = {}

    def to_xml_element(self, et: Any):
        root = et.Element("canvas", self._xml_attrs())
        for child in self:
            if not isinstance(child, Layer):
                raise TypeError(
                    f"Canvas children must be Layer instances, got {type(child).__name__}"
                )
            root.append(child.to_xml_element(et))
        return root

    def save_xml(self, filename):
        from xml.etree import ElementTree as et

        root = self.to_xml_element(et)

        tree = et.ElementTree(root)
        et.indent(tree, space="    ")

        tree.write(filename, encoding="UTF-8", xml_declaration=True)
