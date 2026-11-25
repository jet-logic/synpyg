"""Basic Math & Logic ValueNodes for Synfig."""

from .value import ValueNode
from .ref import Ref


class BinaryOp(ValueNode):
    """Base class for binary operations (add, subtract, multiply, divide)."""

    def __init__(self, lhs, rhs, **kwargs):
        super().__init__(**kwargs)
        self.links["lhs"] = lhs
        self.links["rhs"] = rhs


class Add(BinaryOp):
    """Adds two values."""

    node_type = "add"


class Subtract(BinaryOp):
    """Subtracts rhs from lhs."""

    node_type = "subtract"


class Multiply(BinaryOp):
    """Multiplies two values."""

    node_type = "multiply"


class Divide(BinaryOp):
    """Divides lhs by rhs."""

    node_type = "divide"


class Switch(ValueNode):
    """Selects between two values based on a boolean condition."""

    node_type = "switch"

    def __init__(self, condition, if_true, if_false, **kwargs):
        super().__init__(**kwargs)
        self.links["condition"] = condition
        self.links["if_true"] = if_true
        self.links["if_false"] = if_false


class Step(ValueNode):
    """Outputs 'before' value until 'time', then outputs 'after' value."""

    node_type = "step"

    def __init__(self, time, before, after, **kwargs):
        super().__init__(**kwargs)
        self.links["time"] = time
        self.links["before"] = before
        self.links["after"] = after
