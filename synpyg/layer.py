from .animated import Animated
from .base import Base, Param, WithXML, WithFields
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


def _animated_times(value, seen: set):
    """Yield the waypoint times of ``value`` if it is (or refers to) an Animated.

    Refs are followed, and an Animated reached twice (shared, or in a cycle)
    is read once. Plain ``use`` strings cannot be resolved and are skipped."""
    stack = [value]
    while stack:
        v = stack.pop()
        if isinstance(v, Ref):
            v = v.target
        if isinstance(v, Animated) and id(v) not in seen:
            seen.add(id(v))
            for w in v.waypoints:
                if (t := w.__dict__.get("time")) is not None:
                    yield t
                stack.append(w.__dict__.get("value"))  # an Animated may nest a Ref


def _times_under(root):
    """Yield every waypoint time of ``root``'s params and of all layers below it."""
    seen: set = set()
    stack = [root]
    while stack:
        node = stack.pop()
        if isinstance(node, Layer):
            for _, prop in node._enum_params():
                yield from _animated_times(prop.value, seen)
        if isinstance(node, Grouping):
            stack.extend(node)


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


class Grouping(Base):
    def time_range(self) -> tuple[float, float] | None:
        """The earliest and latest waypoint time, in seconds, over the whole
        layer hierarchy below (and, for a group layer, including) this node.

        Animations a param refers to with ``Ref`` count too. Returns ``None``
        when nothing is animated."""
        times = list(_times_under(self))
        return (min(times), max(times)) if times else None

    def add_solid_color_layer(self, *args, before: Base | None = None, **kwargs):
        e = SolidColorLayer(*args, **kwargs)
        self.insert_before(before, e)
        return e

    def add_circle_layer(self, *args, before: Base | None = None, **kwargs):
        layer = CircleLayer(*args, **kwargs)
        self.insert_before(before, layer)
        return layer

    def add_rectangle_layer(self, *args, before: Base | None = None, **kwargs):
        layer = RectangleLayer(*args, **kwargs)
        self.insert_before(before, layer)
        return layer

    def add_region_layer(self, *args, before: Base | None = None, **kwargs):
        layer = RegionLayer(*args, **kwargs)
        self.insert_before(before, layer)
        return layer

    def add_outline_layer(self, *args, before: Base | None = None, **kwargs):
        layer = OutlineLayer(*args, **kwargs)
        self.insert_before(before, layer)
        return layer

    def add_advanced_outline_layer(self, *args, before: Base | None = None, **kwargs):
        layer = AdvancedOutlineLayer(*args, **kwargs)
        self.insert_before(before, layer)
        return layer

    def add_group_layer(self, *args, before: Base | None = None, **kwargs):
        layer = GroupLayer(*args, **kwargs)
        self.insert_before(before, layer)
        return layer

    def add_linear_gradient_layer(self, *args, before: Base | None = None, **kwargs):
        layer = LinearGradientLayer(*args, **kwargs)
        self.insert_before(before, layer)
        return layer

    def add_radial_gradient_layer(self, *args, before: Base | None = None, **kwargs):
        layer = RadialGradientLayer(*args, **kwargs)
        self.insert_before(before, layer)
        return layer

    def add_conical_gradient_layer(self, *args, before: Base | None = None, **kwargs):
        layer = ConicalGradientLayer(*args, **kwargs)
        self.insert_before(before, layer)
        return layer

    def add_spiral_gradient_layer(self, *args, before: Base | None = None, **kwargs):
        layer = SpiralGradientLayer(*args, **kwargs)
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


# Synfig registers the PasteCanvas name as an alias for its group layer.
PasteCanvasLayer = GroupLayer
