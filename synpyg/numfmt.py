import math


def fmt_num(x: float) -> str:
    """Format a finite number using Python's shortest round-trip representation."""
    if not math.isfinite(x):
        raise ValueError(f"Cannot format non-finite number {x!r}")

    s = repr(x)

    # Keep integer-valued floats compact: 24.0 -> 24
    if s.endswith(".0"):
        s = s[:-2]

    return "0" if s in ("-0", "") else s
