from typing import Any, Optional, TYPE_CHECKING
from pathlib import Path
from .layer import CircleLayer, GroupLayer, Layer, MotionBlurLayer, SolidColorLayer
from .base import Base


class Canvas(Base):
    """
    A Synfig canvas
    """

    def __init__(
        self,
        version="1.2",
        width=480,
        height=1080,
        fps=24.0,
        begin_time: Optional[float | str | int] = None,
        end_time: Optional[float | str | int] = None,
        view_box: Optional[str] = None,
        **kwargs,
    ):
        super().__init__()
        self.version = version
        self.width = width
        self.height = height
        self.fps = fps
        self.begin_time = begin_time
        self.end_time = end_time
        self.view_box = view_box
        self.meta: dict[str, Any] = {}

    def to_xml_element(self):
        attributes = {
            "version": str(self.version),
            "width": str(self.width),
            "height": str(self.height),
            "fps": str(self.fps),
        }

        if self.begin_time is not None:
            attributes["begin-time"] = str(self.begin_time)

        if self.end_time is not None:
            attributes["end-time"] = str(self.end_time)

        if self.view_box is not None:
            attributes["view-box"] = str(self.view_box)

        root = ET.Element("canvas", attributes)

        for child in self:
            if not hasattr(child, "to_xml_element"):
                raise TypeError(f"Cannot serialize {type(child).__name__}")
            assert isinstance(child, Layer)

            root.append(child.to_xml_element())

        return root

    def save_xml(self, filename):
        import xml.etree.ElementTree as ET

        path = Path(filename)

        if path.suffix.lower() != ".sif":
            path = path.with_suffix(".sif")

        root = self.to_xml_element()

        tree = ET.ElementTree(root)
        ET.indent(tree, space="    ")

        tree.write(
            path,
            encoding="UTF-8",
            xml_declaration=True,
        )

        return path

    def add_solid_color_layer(self, *args, before: Base | None = None, **kwargs):
        e = SolidColorLayer(*args, **kwargs)
        self.insert_before(before, e)
        return e

    def add_circle_layer(self, *args, before: Base | None = None, **kwargs):
        layer = CircleLayer(*args, **kwargs)
        self.insert_before(before, layer)
        return layer

    def add_group_layer(self, *args, before: Base | None = None, **kwargs):
        layer = GroupLayer(*args, **kwargs)
        self.insert_before(before, layer)
        return layer

    def add_motion_blur_layer(self, *args, before: Base | None = None, **kwargs):
        layer = MotionBlurLayer(*args, **kwargs)
        self.insert_before(before, layer)
        return layer


from xml.etree import ElementTree as ET
