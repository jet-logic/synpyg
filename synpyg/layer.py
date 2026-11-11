from dataclasses import dataclass, fields
from typing import Optional
from .valuenode import WithXML
from .value import Color, Integer, Real, Time, Vector, Boolean
from .base import Base, Property, param


@dataclass(eq=False, kw_only=True, init=False)
class WithParams:

    def _enum_params(self):
        for k, v in self.__dict__.items():
            if isinstance(v, Property):
                yield k, v

    def __getattr__(self, name):
        for f in fields(self):
            if f.name == name:
                if m := f.metadata.get("parm"):
                    p = Property()
                    p.typed = m.get("typed")
                    p.name = m.get("name")
                    setattr(self, name, p)
                    return p
        try:
            return super().__getattr__(name)  # type: ignore
        except AttributeError:
            raise AttributeError(
                f"{self.__class__.__name__!r} has no attribute {name!r}"
            ) from None

    def set_params(self, **kwargs):
        def _set(k, v):
            for f in fields(self):
                if f.name == k:
                    if m := f.metadata.get("parm"):
                        p = Property()
                        p.name = f.name
                        p.typed = m.get("typed")
                        p.set_value(v)
                        setattr(self, k, p)
                        return
            raise NameError(f"Unknow params {k}?")

        for k, v in kwargs.items():
            _set(k, v)

        return self


@dataclass(eq=False, kw_only=True, init=False)
class Layer(WithParams, WithXML, Base):
    """
    A Synfig layer
    """

    TAG = "layer"
    z_depth: Property = param("z_depth", Real)
    amount: Property = param("amount", Real)
    blend_method: Property = param("blend_method", Integer)

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

        # Initialize and serialize all declared parameters
        for name, prop in self._enum_params():
            element.append(prop.to_xml_element())

        return element


@dataclass(eq=False, kw_only=True, init=False)
class SolidColorLayer(Layer):

    color: Property = param("color", Color)

    def __init__(self, desc="", **kwargs):
        super().__init__("solid_color", version="0.1", desc=desc, **kwargs)


@dataclass(eq=False, kw_only=True, init=False)
class CircleLayer(Layer):

    color: Property = param("color", Color)
    radius: Property = param("radius", Real)
    feather: Property = param("feather", Real)
    origin: Property = param("origin", Vector)
    invert: Property = param("invert", Boolean)
    falloff: Property = param("falloff", Integer)

    def __init__(self, desc="", **kwargs):
        super().__init__("circle", version="0.1", desc=desc, **kwargs)


@dataclass(eq=False, kw_only=True, init=False)
class MotionBlurLayer(Layer):
    """
    A Synfig Motion Blur layer with all standard parameters.
    """

    aperture: Property = param("aperture", Time)
    subsamples_factor: Property = param("subsamples_factor", Real)
    subsampling_type: Property = param("subsampling_type", Integer)
    subsample_start: Property = param("subsample_start", Real)
    subsample_end: Property = param("subsample_end", Real)

    def __init__(self, desc="", **kwargs):
        super().__init__("motion_blur", version="0.1", desc=desc, **kwargs)


@dataclass(eq=False, kw_only=True, init=False)
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


@dataclass(eq=False, kw_only=True, init=False)
class GroupLayer(Layer, Grouping):
    """
    A Synfig Group layer that can either contain inline child layers
    or reference an external/exported canvas via the 'use' attribute.
    """

    origin: Property = param("origin", Vector)

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
                if not hasattr(child, "to_xml_element"):
                    raise TypeError(f"Cannot serialize {type(child).__name__}")
                assert isinstance(child, Layer)
                sub_canvas.append(child.to_xml_element())

        return element
