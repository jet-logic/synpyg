import xml.etree.ElementTree as ET
from typing import Dict, Optional
from .value import Integer, Real
from .base import Base, Field, Property, param, params


class Layer(Base):
    """
    A Synfig layer
    """

    TAG = "layer"

    def __init__(
        self,
        type: str,
        version: str,
        desc: Optional[str] = None,
        active: bool = True,
        exclude_from_rendering: bool = False,
        group: Optional[str] = None,
    ):
        self.type: str = type
        self.version: str = version
        self.desc: Optional[str] = desc
        self.active: bool = active
        self.exclude_from_rendering: bool = exclude_from_rendering
        self.group: Optional[str] = group

    def __init_subclass__(cls, /, **kwargs):
        super().__init_subclass__(**kwargs)
        _params: list[tuple[str, Field, object]] = []
        for k, v in tuple(cls.__dict__.items()):
            if isinstance(v, Field):
                delattr(cls, k)
                _params.append((k, v, cls.__annotations__.get(k)))
        # print("__init_subclass__", cls, _params)
        cls._params = _params

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

    def _enum_params(self):
        for k, v in self.__dict__.items():
            if isinstance(v, Property):
                assert not isinstance(v, Field)
                yield k, v


class SolidColorLayer(Layer):
    z_depth: Property = param("z_depth", Real, 0.0)
    amount: Property = param("amount", Real, 1.0)
    blend_method: Property = param("blend_method", Integer, 1)

    def __init__(self):
        super().__init__("solid", "1.0")
