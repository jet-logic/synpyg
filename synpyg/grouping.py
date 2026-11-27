"""Shared layer-container behaviour for canvases and group layers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Base

if TYPE_CHECKING:
    from .layer import Layer


def _animated_times(value, seen: set):
    """Yield waypoint times from an Animated value, following object Refs."""
    from .animated import Animated
    from .ref import Ref

    stack = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, Ref):
            current = current.target
        if isinstance(current, Animated) and id(current) not in seen:
            seen.add(id(current))
            for waypoint in current.waypoints:
                if (time := waypoint.__dict__.get("time")) is not None:
                    yield time
                stack.append(waypoint.__dict__.get("value"))


def _times_under(root):
    """Yield every waypoint time of the params and nested layers below root."""
    from .layer import Layer

    seen: set = set()
    stack = [root]
    while stack:
        node = stack.pop()
        if isinstance(node, Layer):
            for _, prop in node._enum_params():
                yield from _animated_times(prop.value, seen)
        if isinstance(node, Grouping):
            stack.extend(node)


class Grouping(Base):
    """A tree-like container of Synfig layers."""

    def enum_layer_type(self, kind: type):
        """Yield descendant layers that are instances of ``kind``.

        The traversal is depth-first in layer order. Matching group layers are
        yielded before searching their nested canvases.
        """
        from .layer import Layer

        stack = list(reversed(list(self)))
        while stack:
            layer = stack.pop()
            if isinstance(layer, Layer) and isinstance(layer, kind):
                yield layer
            if isinstance(layer, Grouping):
                stack.extend(reversed(list(layer)))

    def find_layer(
        self,
        index: int | str,
        kind: type[Layer],
        default: Layer | None = None,
    ) -> Layer:
        """Find a descendant layer by its zero-based index or description.

        String indexes match ``layer.desc`` exactly. If descriptions are not
        unique, the first matching layer in depth-first layer order is returned.
        """
        if isinstance(index, str):
            for layer in self.enum_layer_type(kind):
                if getattr(layer, "desc", None) == index:
                    return layer

            if default is not None:
                return default
            raise LookupError(f"no descendant <{kind.__name__}> with desc={index!r}")

        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError("index must be an integer or a description string")
        if index < 0:
            raise IndexError("index must be non-negative")

        for position, layer in enumerate(self.enum_layer_type(kind)):
            if position == index:
                return layer

        if default is not None:
            return default
        raise IndexError(f"no descendant <{kind.__name__}> at index {index}")

    def time_range(self) -> tuple[float, float] | None:
        """Return the earliest/latest waypoint time below this container."""
        times = list(_times_under(self))
        return (min(times), max(times)) if times else None

    def add_solid_color_layer(self, *args, before: Base | None = None, **kwargs):
        from .layer import SolidColorLayer

        layer = SolidColorLayer(*args, **kwargs)
        self.insert_before(before, layer)
        return layer

    def add_circle_layer(self, *args, before: Base | None = None, **kwargs):
        from .layer import CircleLayer

        layer = CircleLayer(*args, **kwargs)
        self.insert_before(before, layer)
        return layer

    def add_rectangle_layer(self, *args, before: Base | None = None, **kwargs):
        from .layer import RectangleLayer

        layer = RectangleLayer(*args, **kwargs)
        self.insert_before(before, layer)
        return layer

    def add_region_layer(self, *args, before: Base | None = None, **kwargs):
        from .layer import RegionLayer

        layer = RegionLayer(*args, **kwargs)
        self.insert_before(before, layer)
        return layer

    def add_outline_layer(self, *args, before: Base | None = None, **kwargs):
        from .layer import OutlineLayer

        layer = OutlineLayer(*args, **kwargs)
        self.insert_before(before, layer)
        return layer

    def add_advanced_outline_layer(self, *args, before: Base | None = None, **kwargs):
        from .layer import AdvancedOutlineLayer

        layer = AdvancedOutlineLayer(*args, **kwargs)
        self.insert_before(before, layer)
        return layer

    def add_group_layer(self, *args, before: Base | None = None, **kwargs):
        from .layer import GroupLayer

        layer = GroupLayer(*args, **kwargs)
        self.insert_before(before, layer)
        return layer

    def add_linear_gradient_layer(self, *args, before: Base | None = None, **kwargs):
        from .layer import LinearGradientLayer

        layer = LinearGradientLayer(*args, **kwargs)
        self.insert_before(before, layer)
        return layer

    def add_radial_gradient_layer(self, *args, before: Base | None = None, **kwargs):
        from .layer import RadialGradientLayer

        layer = RadialGradientLayer(*args, **kwargs)
        self.insert_before(before, layer)
        return layer

    def add_conical_gradient_layer(self, *args, before: Base | None = None, **kwargs):
        from .layer import ConicalGradientLayer

        layer = ConicalGradientLayer(*args, **kwargs)
        self.insert_before(before, layer)
        return layer

    def add_spiral_gradient_layer(self, *args, before: Base | None = None, **kwargs):
        from .layer import SpiralGradientLayer

        layer = SpiralGradientLayer(*args, **kwargs)
        self.insert_before(before, layer)
        return layer

    def add_motion_blur_layer(self, *args, before: Base | None = None, **kwargs):
        from .layer import MotionBlurLayer

        layer = MotionBlurLayer(*args, **kwargs)
        self.insert_before(before, layer)
        return layer

    def add_external_canvas_layer(
        self, use: str, *args, before: Base | None = None, **kwargs
    ):
        """Compatibility helper; external canvases are now ordinary group layers."""
        from .canvas import Canvas

        return self.add_group_layer(
            *args, before=before, canvas=Canvas(use=use), **kwargs
        )
