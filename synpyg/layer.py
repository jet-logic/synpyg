from .base import Base, Param, WithXML, WithFields
from .canvas import Canvas
from .grouping import Grouping
from .ref import Ref
from .value import (
    Angle,
    Color,
    DashItemList,
    Gradient,
    Integer,
    Real,
    Time,
    Vector,
    Boolean,
    Spline,
    Transformation,
    WidthPointList,
)
from .attrs import BoolAttr, StringAttr


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
        attrs = self._xml_attrs()
        attrs.update(self.__dict__.get("_extra_xml_attrs", {}))
        element = et.Element("layer", attrs)
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
    type = Param(Integer)

    def __init__(self, desc="", **kwargs):
        super().__init__("circle", version="0.1", desc=desc, **kwargs)


class RectangleLayer(Layer):
    """Synfig rectangle primitive."""

    color = Param(Color)
    point1 = Param(Vector)
    point2 = Param(Vector)
    expand = Param(Real)
    invert = Param(Boolean)

    def __init__(self, desc="", **kwargs):
        super().__init__("rectangle", version="0.1", desc=desc, **kwargs)


class _ShapeLayer(Layer):
    color = Param(Color)
    origin = Param(Vector)
    invert = Param(Boolean)
    antialias = Param(Boolean)
    feather = Param(Real)
    blurtype = Param(Integer)
    winding_style = Param(Integer)
    bline = Param(Spline)


class RegionLayer(_ShapeLayer):
    """Filled spline region."""

    def __init__(self, desc="", **kwargs):
        super().__init__("region", version="0.1", desc=desc, **kwargs)


class OutlineLayer(_ShapeLayer):
    """Stroked spline outline."""

    width = Param(Real)
    expand = Param(Real)
    sharp_cusps = Param(Boolean)
    round_tip_begin = Param(Boolean, name="round_tip[0]")
    round_tip_end = Param(Boolean, name="round_tip[1]")
    loopyness = Param(Real)
    homogeneous_width = Param(Boolean)

    def __init__(self, desc="", **kwargs):
        super().__init__("outline", version="0.1", desc=desc, **kwargs)


class _GradientLayer(Layer):
    """Shared gradient parameter for Synfig's geometric gradient layers."""

    gradient = Param(Gradient)


class LinearGradientLayer(_GradientLayer):
    p1 = Param(Vector)
    p2 = Param(Vector)
    loop = Param(Boolean)
    zigzag = Param(Boolean)

    def __init__(self, desc="", **kwargs):
        super().__init__("linear_gradient", version="0.0", desc=desc, **kwargs)


class RadialGradientLayer(_GradientLayer):
    center = Param(Vector)
    radius = Param(Real)
    loop = Param(Boolean)
    zigzag = Param(Boolean)

    def __init__(self, desc="", **kwargs):
        super().__init__("radial_gradient", version="0.1", desc=desc, **kwargs)


class ConicalGradientLayer(_GradientLayer):
    center = Param(Vector)
    light_angle = Param(Angle)
    symmetric = Param(Boolean)

    def __init__(self, desc="", **kwargs):
        super().__init__("conical_gradient", version="0.1", desc=desc, **kwargs)


class SpiralGradientLayer(_GradientLayer):
    center = Param(Vector)
    radius = Param(Real)
    angle = Param(Angle)
    clockwise = Param(Boolean)

    def __init__(self, desc="", **kwargs):
        super().__init__("spiral_gradient", version="0.1", desc=desc, **kwargs)


class AdvancedOutlineLayer(_ShapeLayer):
    """Variable-width spline outline with optional dash pattern."""

    width = Param(Real)
    expand = Param(Real)
    start_tip = Param(Integer)
    end_tip = Param(Integer)
    cusp_type = Param(Integer)
    smoothness = Param(Real)
    homogeneous = Param(Boolean)
    wplist = Param(WidthPointList)
    fast = Param(Boolean)
    dash_enabled = Param(Boolean)
    dilist = Param(DashItemList)
    dash_offset = Param(Real)

    def __init__(self, desc="", **kwargs):
        super().__init__("advanced_outline", version="0.3", desc=desc, **kwargs)


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


class GroupLayer(Layer, Grouping):
    origin = Param(Vector)
    transformation = Param(Transformation)
    speed = Param(Real)
    zoom = Param(Real)
    time_offset = Param(Time)
    lock_selection = Param(Boolean)
    focus = Param(Vector)
    outline_grow = Param(Real)
    z_range = Param(Boolean)
    z_range_position = Param(Real)
    z_range_depth = Param(Real)
    z_range_blur = Param(Real)
    canvas = Param(Canvas)

    def __init__(self, desc="", *, canvas=None, **kwargs):
        super().__init__("group", version="0.1", desc=desc, **kwargs)
        self.canvas = Canvas() if canvas is None else canvas

    def _canvas_value(self) -> Canvas:
        value = self.canvas.value
        if isinstance(value, Ref):
            raise TypeError("an externally referenced group canvas has no editable local layer tree")
        if not isinstance(value, Canvas):
            raise TypeError("GroupLayer.canvas must contain a Canvas or Ref")
        return value

    # Keep the established Grouping API, but make the Canvas value the actual
    # owner of the child layers instead of maintaining a second child list.
    def __iter__(self):
        value = self.canvas.value
        if isinstance(value, Ref):
            return iter(())
        return iter(self._canvas_value())

    def insert_before(self, which, *nodes):
        return self._canvas_value().insert_before(which, *nodes)

    def append_child(self, *nodes):
        return self._canvas_value().append_child(*nodes)

    def first_child(self):
        return self._canvas_value().first_child()

    def last_child(self):
        return self._canvas_value().last_child()

    def remove_children(self):
        return self._canvas_value().remove_children()

    def children(self):
        return iter(self)


# Synfig registers the PasteCanvas name as an alias for its group layer.
PasteCanvasLayer = GroupLayer
