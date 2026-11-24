"""Descriptor-based typed fields, reusable on their own.

This package must not import anything from the rest of this module: it only
depends on the standard library and on itself (relative imports), so the
folder can be copied into another project as-is.
"""

from .attr import Attr
from .base import Field, Wrapped, iter_attrs, iter_descriptors, iter_fields, unwrap
from .declarative import Declarative
from .kind import Kind

__all__ = [
    "Attr",
    "Declarative",
    "Field",
    "Kind",
    "Wrapped",
    "iter_attrs",
    "iter_descriptors",
    "iter_fields",
    "unwrap",
]
