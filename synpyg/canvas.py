from typing import Any, Optional
from pathlib import Path
from .valuenode import WithXML
from .layer import Grouping, Layer


class Canvas(WithXML, Grouping):
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

        root = self._etree.Element("canvas", attributes)

        for child in self:
            if not isinstance(child, Layer):
                raise TypeError(
                    f"Canvas children must be Layer instances, got {type(child).__name__}"
                )
            root.append(child.to_xml_element())

        return root

    def save_xml(self, filename):

        path = Path(filename)

        if path.suffix.lower() != ".sif":
            path = path.with_suffix(".sif")

        root = self.to_xml_element()

        tree = self._etree.ElementTree(root)
        self._etree.indent(tree, space="    ")

        tree.write(
            path,
            encoding="UTF-8",
            xml_declaration=True,
        )

        return path
