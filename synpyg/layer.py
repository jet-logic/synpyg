from typing import Optional
from .valuenode import WithXML
from .value import Color, Integer, Real, Time, Vector, Boolean
from .base import Base, Param, WithParams


class Layer(WithParams, WithXML, Base):
    """
    A Synfig layer
    """

    TAG = "layer"
    z_depth = Param(Real)
    amount = Param(Real)
    blend_method = Param(Integer)

    def __init__(
        self,
        type: str,
        version: str = "0.1",
        desc: Optional[str] = None,
        active: bool = True,
        exclude_from_rendering: bool = False,
        group: Optional[str] = None,
    ):
        super().__init__()
        self.type: str = type
        self.version: str = version
        self.desc: Optional[str] = desc
        self.active: bool = active
        self.exclude_from_rendering: bool = exclude_from_rendering
        self.group: Optional[str] = group

    def to_xml_element(self):
        element = self._etree.Element(
            "layer",
            {
                "type": self.type,
                "version": self.version,
            },
        )

        if self.desc is not None:
            element.set("desc", self.desc)

        if self.active is not None:
            element.set("active", str(self.active).lower())

        if self.exclude_from_rendering:
            element.set("exclude_from_rendering", "true")

        if self.group is not None:
            element.set("group", self.group)

        # Declared params in declaration order, then ad-hoc ones; unset ones are skipped
        for _, prop in self._enum_params():
            if prop.has_value:
                element.append(prop.to_xml_element())

        return element


class SolidColorLayer(Layer):

    color = Param(Color)

    def __init__(self, desc="", **kwargs):
        super().__init__("solid_color", version="0.1", desc=desc, **kwargs)


class CircleLayer(Layer):

    color = Param(Color)
    radius = Param(Real)
    feather = Param(Real)
    origin = Param(Vector)
    invert = Param(Boolean)
    falloff = Param(Integer)

    def __init__(self, desc="", **kwargs):
        super().__init__("circle", version="0.1", desc=desc, **kwargs)


class MotionBlurLayer(Layer):
    """
    A Synfig Motion Blur layer with all standard parameters.
    """

    aperture = Param(Time)
    subsamples_factor = Param(Real)
    subsampling_type = Param(Integer)
    subsample_start = Param(Real)
    subsample_end = Param(Real)

    def __init__(self, desc="", **kwargs):
        super().__init__("motion_blur", version="0.1", desc=desc, **kwargs)


class Grouping(Base):
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


class GroupLayer(Layer, Grouping):
    """
    A Synfig Group layer that can either contain inline child layers
    or reference an external/exported canvas via the 'use' attribute.
    """

    origin = Param(Vector)

    def __init__(self, desc="", use: Optional[str] = None, **kwargs):
        super().__init__("group", version="0.1", desc=desc, **kwargs)
        self.use = use

    def to_xml_element(self):
        element = super().to_xml_element()

        canvas_param = self._etree.SubElement(element, "param", {"name": "canvas"})

        if self.use:
            # If using a reference, set the 'use' attribute on the canvas element
            self._etree.SubElement(canvas_param, "canvas", {"use": self.use})
        else:
            # Otherwise, serialize inline child layers as before
            sub_canvas = self._etree.SubElement(canvas_param, "canvas")
            for child in self:
                if not isinstance(child, Layer):
                    raise TypeError(
                        f"GroupLayer children must be Layer instances, got {type(child).__name__}"
                    )
                sub_canvas.append(child.to_xml_element())

        return element
