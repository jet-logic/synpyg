import math
import unittest
from xml.etree import ElementTree as ET
from synpyg.layer import Layer
from synpyg.animated import Animated
from synpyg.base import Param
from synpyg.value import Angle, Color, String, Vector
from synpyg.numeric import to_float, to_int
from synpyg.field import QuadFloatAttr


class StringAngleValueTest(unittest.TestCase):
    def test_string_constructs_with_data(self):
        s = String("hello")
        self.assertEqual(s.data, "hello")
        # self.assertIsNone(s.id)
        self.assertEqual(s.to_xml_element(ET).attrib, {"value": "hello"})

    def test_string_keeps_identifiers(self):
        s = String("x", id="foo", guid="bar")
        self.assertEqual((s.id, s.guid), ("foo", "bar"))

    def test_string_check_value(self):
        self.assertIsInstance(String.check_value("a"), String)
        for bad in (True, 1, 1.5, None, ["x"]):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    String.check_value(bad)

    def test_string_coerce_passthrough(self):
        s = String("x")
        self.assertIs(String.coerce(s), s)
        self.assertEqual(String.coerce("y").data, "y")

    def test_angle_constructs_and_serializes(self):
        a = Angle(90)
        self.assertEqual(a.data, 90.0)
        self.assertIsInstance(a.data, float)
        self.assertEqual(a.to_xml_element(ET).attrib, {"value": "90"})

    def test_angle_check_value(self):
        self.assertIsInstance(Angle.check_value(1.5), Angle)
        self.assertIsInstance(Angle.check_value("45"), Angle)
        with self.assertRaises(ValueError):
            Angle.check_value(object())

    def test_string_via_param(self):
        class L(Layer):
            label = Param(String)

        lyr = L("x")  # type: ignore[call-arg]
        lyr.label = "hello"  # type: ignore[attr-defined]
        self.assertIsInstance(lyr.label.value, String)  # type: ignore[attr-defined]
        self.assertEqual(
            lyr.to_xml_element(ET).find("param").find("string").get("value"),  # type: ignore[union-attr]
            "hello",
        )
        with self.assertRaises(ValueError):
            lyr.label = 42  # type: ignore[attr-defined]

    def test_string_via_animated(self):
        a = Animated(String)
        a.add_waypoint(0, "a").add_waypoint(1, String("b"))
        vals = [w.value.data for w in a.waypoints]
        self.assertEqual(vals, ["a", "b"])


class ValueShapeTest(unittest.TestCase):
    def test_color_rejects_wrong_length(self):
        for bad in ([], [1], [1, 2], [1, 2, 3], [1, 2, 3, 4, 5]):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    Color(bad)  # type: ignore

    def test_vector_rejects_wrong_length(self):
        for bad in ([], [1], [1, 2, 3]):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    Vector(bad)  # type: ignore

    def test_color_accepts_list_and_tuple(self):
        self.assertEqual(Color([1, 2, 3, 4]).data, (1.0, 2.0, 3.0, 4.0))
        self.assertEqual(Color((1, 2, 3, 4)).data, (1.0, 2.0, 3.0, 4.0))


class NumericConversionTests(unittest.TestCase):
    def test_float_conversion(self):
        self.assertEqual(to_float(2), 2.0)
        self.assertEqual(to_float("2.5"), 2.5)

    def test_integer_conversion(self):
        self.assertEqual(to_int(2.0), 2)
        self.assertEqual(to_int("2"), 2)
        # self.assertEqual(to_int("2.0"), 2)

    def test_integer_rejects_fractional_values(self):
        for value in (2.5, "2.5"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    to_int(value)

    def test_rejects_booleans(self):
        for converter in (to_float, to_int):
            with self.subTest(converter=converter):
                with self.assertRaises(ValueError):
                    converter(True)

    def test_rejects_non_finite_values(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    to_float(value)

    def test_vector_rejects_invalid_components(self):
        for values in (
            [1, True],
            [1, math.nan],
            [1, math.inf],
        ):
            with self.subTest(values=values):
                with self.assertRaises((TypeError, ValueError)):
                    Vector(values)

    def test_color_rejects_invalid_components(self):
        with self.assertRaises((TypeError, ValueError)):
            Color([0, 0, 0, math.nan])

    def test_quad_float_rejects_boolean(self):
        class Example:
            box = QuadFloatAttr()

        with self.assertRaises(ValueError):
            Example().box = (1, 2, True, 4)


class TestVectorColorCoerce(unittest.TestCase):
    def test_vector_coerce_accepts_iterables(self):
        self.assertEqual(Vector.coerce(range(2)).data, (0.0, 1.0))
        self.assertEqual(Vector.coerce(iter([1, 2])).data, (1.0, 2.0))

    def test_color_coerce_accepts_iterables(self):
        self.assertEqual(Color.coerce(range(4)).data, (0.0, 1.0, 2.0, 3.0))
        self.assertEqual(
            Color.coerce(iter([1, 0, 0, 1])).data,
            (1.0, 0.0, 0.0, 1.0),
        )

    def test_vector_coerce_rejects_strings(self):
        with self.assertRaises(ValueError):
            Vector.coerce("12")

    def test_color_coerce_rejects_strings(self):
        with self.assertRaises(ValueError):
            Color.coerce("1234")


class VectorColorInputTest(unittest.TestCase):
    def test_vector_rejects_strings(self):
        for value in ("12", b"12", bytearray(b"12")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Vector(value)

                with self.assertRaises(ValueError):
                    Vector.coerce(value)

    def test_color_rejects_strings(self):
        for value in ("1234", b"1234", bytearray(b"1234")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Color(value)

                with self.assertRaises(ValueError):
                    Color.coerce(value)

    def test_numeric_iterables_still_work(self):
        self.assertEqual(Vector([1, 2]).data, (1.0, 2.0))
        self.assertEqual(Color((1, 0, 0, 1)).data, (1.0, 0.0, 0.0, 1.0))

    def test_wrong_component_count_is_rejected(self):
        with self.assertRaises(ValueError):
            Vector([1, 2, 3])

        with self.assertRaises(ValueError):
            Color([1, 2, 3])


if __name__ == "__main__":
    unittest.main()
