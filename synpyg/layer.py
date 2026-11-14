from synpyg.base import WithXML
from synpyg.base import Base, Param
from synpyg.base import WithFields
from synpyg.value import Color, Integer, Real, Time, Vector, Boolean
from synpyg.field import BoolAttr, StringAttr


class Layer(WithFields, WithXML, Base):
    TAG = "layer"

    # XML attributes of <layer>
    layer_type = StringAttr(name="type", required=True)
    version = StringAttr(required=True)
    desc = StringAttr()
    active = BoolAttr(required=True)
    exclude_from_rendering = BoolAttr()
    group = StringAttr()

    # <param>s
    z_depth = Param(Real)
    amount = Param(Real)
    blend_method = Param(Integer)

    def __init__(
        self,
        type: str,
        version="0.1",
        desc=None,
        active=True,
        exclude_from_rendering=False,
        group=None,
    ):
        super().__init__()
        self.layer_type = type
        self.version = version
        if desc is not None:
            self.desc = desc
        self.active = active
        self.exclude_from_rendering = exclude_from_rendering
        if group is not None:
            self.group = group

    def to_xml_element(self, et):
        element = et.Element("layer", self._xml_attrs())
        for _, prop in self._enum_params():
            if prop.has_value:
                element.append(prop.to_xml_element(et))
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

    def add_external_canvas_layer(
        self, use: str, *args, before: Base | None = None, **kwargs
    ):
        layer = ExternalCanvasLayer(use, *args, **kwargs)
        self.insert_before(before, layer)
        return layer


class GroupLayer(Layer, Grouping):
    origin = Param(Vector)

    def __init__(self, desc="", **kwargs):
        super().__init__("group", version="0.1", desc=desc, **kwargs)

    def to_xml_element(self, et):
        element = super().to_xml_element(et)

        canvas_param = et.SubElement(element, "param", {"name": "canvas"})
        sub_canvas = et.SubElement(canvas_param, "canvas")

        for child in self:
            if not isinstance(child, Layer):
                raise TypeError(
                    f"GroupLayer children must be Layer instances, "
                    f"got {type(child).__name__}"
                )
            sub_canvas.append(child.to_xml_element(et))

        return element


class ExternalCanvasLayer(Layer):
    origin = Param(Vector)

    def __init__(self, use: str, desc="", **kwargs):
        if not isinstance(use, str) or not use:
            raise ValueError("External canvas reference must be a non-empty string")

        super().__init__("group", version="0.1", desc=desc, **kwargs)
        self.use = use

    def to_xml_element(self, et):
        element = super().to_xml_element(et)

        canvas_param = et.SubElement(element, "param", {"name": "canvas"})
        et.SubElement(canvas_param, "canvas", {"use": self.use})

        return element
