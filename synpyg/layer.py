from typing import TYPE_CHECKING, Optional
from .value import Color, Integer, Real, Time, Vector, Boolean
from .base import Base, Field, Property, param, params


class WithParams:
    _params: list[tuple[str, Field, object]]

    def __init_subclass__(cls, /, **kwargs):
        super().__init_subclass__(**kwargs)
        _params: list[tuple[str, Field, object]] = []
        for k, v in tuple(cls.__dict__.items()):
            if isinstance(v, Field):
                delattr(cls, k)
                _params.append((k, v, cls.__annotations__.get(k)))
        # print("__init_subclass__", cls, _params)
        cls._params = _params

    def _enum_params(self):
        for k, v in self.__dict__.items():
            if isinstance(v, Property):
                assert not isinstance(v, Field)
                yield k, v

    def __getattr__(self, name):
        for k, g, t in params(self):
            if k == name:
                p = g.producer or t
                a = g.argv
                try:
                    if a is None:
                        v = p()
                    elif isinstance(a, tuple):
                        v = p(*a)
                    else:
                        v = p(a)
                except Exception:
                    from warnings import warn

                    warn(f"__getattr__ {self.__class__.__name__} {k} {(p, a)} {t}")
                    raise
                # print("FIELD", name, v, v.__class__.__name__)
                q = Property(v)
                setattr(self, name, q)
                return q
        try:
            return super().__getattr__(name)  # type: ignore
        except AttributeError:
            raise AttributeError(
                f"{self.__class__.__name__} has no attribute {name}"
            ) from None


class Layer(WithParams, Base):
    """
    A Synfig layer
    """

    TAG = "layer"
    z_depth: Property = param("z_depth", Real, 0.0)
    amount: Property = param("amount", Real, 1.0)
    blend_method: Property = param("blend_method", Integer, 1)

    def __init__(
        self,
        type: str,
        version: str,
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
        element = ET.Element(
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

        # Initialize and serialize all declared parameters
        for name, prop in self._enum_params():
            param = ET.SubElement(element, "param", {"name": name})
            param.append(prop.value.to_xml_element())

        return element


class SolidColorLayer(Layer):

    color: Property = param("color", Color, [0.3, 0.4, 0.5, 0.6])

    def __init__(self, desc="", **kwargs):
        super().__init__("solid_color", version="0.1", desc=desc, **kwargs)


class CircleLayer(Layer):

    color: Property = param("color", Color, [0.3, 0.4, 0.5, 1.0])
    radius: Property = param("radius", Real, 1.0)
    feather: Property = param("feather", Real, 0.0)
    origin: Property = param("origin", Vector, (0.0, 0.0))
    invert: Property = param("invert", Boolean, False)
    falloff: Property = param("falloff", Integer, 1)

    def __init__(self, desc="", **kwargs):
        super().__init__("circle", version="0.1", desc=desc, **kwargs)


class MotionBlurLayer(Layer):
    """
    A Synfig Motion Blur layer with all standard parameters.
    """

    aperture: Property = param("aperture", Time, "0f")
    subsamples_factor: Property = param("subsamples_factor", Real, 1.0)
    subsampling_type: Property = param("subsampling_type", Integer, 0)
    subsample_start_amount: Property = param("subsample_start_amount", Real, 0.0)
    subsample_end_amount: Property = param("subsample_end_amount", Real, 1.0)

    def __init__(self, desc="", **kwargs):
        super().__init__("motion_blur", version="0.1", desc=desc, **kwargs)


class GroupLayer(Layer):
    """
    A Synfig Group layer (pastecanvas) that can either contain inline child layers
    or reference an external/exported canvas via the 'use' attribute.
    """

    origin: Property = param("origin", Vector, (0.0, 0.0))

    def __init__(self, desc="", use: Optional[str] = None, **kwargs):
        super().__init__("paste_canvas", version="0.1", desc=desc, **kwargs)
        self.use = use

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

    def to_xml_element(self):
        element = super().to_xml_element()

        canvas_param = ET.SubElement(element, "param", {"name": "canvas"})

        if self.use:
            # If using a reference, set the 'use' attribute on the canvas element
            ET.SubElement(canvas_param, "canvas", {"use": self.use})
        else:
            # Otherwise, serialize inline child layers as before
            sub_canvas = ET.SubElement(canvas_param, "canvas")
            for child in self:
                if not hasattr(child, "to_xml_element"):
                    raise TypeError(f"Cannot serialize {type(child).__name__}")
                assert isinstance(child, Layer)
                sub_canvas.append(child.to_xml_element())

        return element


from xml.etree import ElementTree as ET
