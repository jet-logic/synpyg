from typing import Any, ClassVar

from .base import Field


class Declarative:
    """Shared ``_assign`` for classes that declare ``Field`` descriptors.

    The implementor owns ``_fields`` (name -> descriptor for everything it
    declares) and is responsible for filling it, e.g. in ``__init_subclass__``.
    """

    _fields: ClassVar[dict[str, Field]]  # annotation only: supplied by the implementor

    def _assign(self, **kwargs):
        for k in kwargs:
            if k not in self._fields:
                raise TypeError(
                    f"{self.__class__.__name__} has no declared parameter {k!r}"
                )

        for k, v in kwargs.items():
            setattr(self, k, v)

        return self

    def _assign_given(self, **kwargs: Any):
        """Like ``_assign``, but arguments that are ``None`` are left unset.

        Names are still checked, so a misspelled keyword is an error even when
        its value is ``None``. Assignment follows keyword order.
        """
        for k in kwargs:
            if k not in self._fields:
                raise TypeError(
                    f"{self.__class__.__name__} has no declared parameter {k!r}"
                )
        return self._assign(**{k: v for k, v in kwargs.items() if v is not None})
