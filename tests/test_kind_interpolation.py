import unittest

from synpyg.fields import Kind
from synpyg.kinds import (
    AngleKind,
    Boolean,
    EnumKind,
    Integer as IntegerKind,
    Number,
    String,
    TimeKind,
    Vec2,
    Vec4,
)
from synpyg.value import (
    Angle,
    Boolean as BoolValue,
    Color,
    Integer,
    Real,
    String as StringValue,
    Time,
    ValueKind,
    Vector,
)


class BaseKindInterpolationTest(unittest.TestCase):
    def test_unsupported_kind_raises_type_error(self):
        with self.assertRaisesRegex(TypeError, "Kind does not support interpolation"):
            Kind().interpolate(1, 2, 0.5)


class PrimitiveKindInterpolationTest(unittest.TestCase):
    def test_float_and_time_are_linear(self):
        self.assertEqual(Number.interpolate(2.0, 6.0, 0.25), 3.0)
        self.assertEqual(TimeKind().interpolate(2.0, 6.0, 0.25), 3.0)

    def test_integer_uses_synfig_rounding(self):
        self.assertEqual(IntegerKind.interpolate(0, 3, 0.5), 2)
        self.assertEqual(IntegerKind.interpolate(-3, 0, 0.5), -1)
        self.assertEqual(IntegerKind.interpolate(-3, -2, 1.0), -2)

    def test_angle_uses_shortest_arc_in_degrees(self):
        self.assertEqual(AngleKind().interpolate(350.0, 10.0, 0.5), 360.0)

    def test_discrete_kinds_hold_until_endpoint(self):
        for kind, start, end in (
            (Boolean, False, True),
            (String, "old", "new"),
            (EnumKind(("a", "b")), "a", "b"),
        ):
            with self.subTest(kind=type(kind).__name__):
                self.assertEqual(kind.interpolate(start, end, 0.99), start)
                self.assertEqual(kind.interpolate(start, end, 1.0), end)

    def test_tuple_kinds_interpolate_componentwise(self):
        self.assertEqual(Vec2.interpolate((0.0, 2.0), (4.0, 6.0), 0.5), (2.0, 4.0))
        self.assertEqual(
            Vec4.interpolate((0.0, 0.0, 0.0, 1.0), (1.0, 0.5, 0.25, 0.0), 0.5),
            (0.5, 0.25, 0.125, 0.5),
        )


class ValueKindInterpolationTest(unittest.TestCase):
    def test_numeric_value_types(self):
        self.assertEqual(
            ValueKind.of(Real).interpolate(Real(2), Real(6), 0.5).data, 4.0
        )
        self.assertEqual(
            ValueKind.of(Integer).interpolate(Integer(0), Integer(3), 0.5).data, 2
        )
        self.assertEqual(
            ValueKind.of(Time).interpolate(Time(2), Time(6), 0.5).data, 4.0
        )
        self.assertEqual(
            ValueKind.of(Angle).interpolate(Angle(350), Angle(10), 0.5).data, 360.0
        )

    def test_vector_and_color_interpolate_componentwise(self):
        self.assertEqual(
            ValueKind.of(Vector).interpolate(Vector((0, 2)), Vector((4, 6)), 0.5).data,
            (2.0, 4.0),
        )
        self.assertEqual(
            ValueKind.of(Color)
            .interpolate(Color((0, 0, 0, 1)), Color((1, 0.5, 0.25, 0)), 0.5)
            .data,
            (0.5, 0.25, 0.125, 0.5),
        )

    def test_boolean_and_string_are_discrete(self):
        self.assertIs(
            ValueKind.of(BoolValue)
            .interpolate(BoolValue(False), BoolValue(True), 0.5)
            .data,
            False,
        )
        self.assertIs(
            ValueKind.of(BoolValue)
            .interpolate(BoolValue(False), BoolValue(True), 1.0)
            .data,
            True,
        )
        self.assertEqual(
            ValueKind.of(StringValue)
            .interpolate(StringValue("a"), StringValue("b"), 0.5)
            .data,
            "a",
        )


if __name__ == "__main__":
    unittest.main()
