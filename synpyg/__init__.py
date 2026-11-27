"""Synpyg: Python tools for creating and reading Synfig animation files."""

from .canvas import Canvas, CanvasKeyframe
from .xmlio import (
    MissingLayerTypeError,
    SIFParseError,
    UnsupportedLayerError,
    UnsupportedValueError,
    load_sif,
    parse_sif,
    register_layer,
    registered_layers,
)

__all__ = [
    "Canvas",
    "CanvasKeyframe",
    "MissingLayerTypeError",
    "SIFParseError",
    "UnsupportedLayerError",
    "UnsupportedValueError",
    "load_sif",
    "parse_sif",
    "register_layer",
    "registered_layers",
]
