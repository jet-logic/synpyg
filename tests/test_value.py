import math
import unittest
from xml.etree import ElementTree as ET
from synpyg.layer import Layer
from synpyg.animated import Animated
from synpyg.base import Param
from synpyg.value import Angle, Color, Segment, String, Vector
from synpyg.numeric import to_float, to_int
from synpyg.attrs import QuadFloatAttr


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
        a.add_keyframe(0, "a").add_keyframe(1, String("b"))
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



class SegmentValueTest(unittest.TestCase):
    def setUp(self):
        self.start = Segment((0, 1), (2, 3), (4, 5), (6, 7))
        self.end = Segment((10, 11), (12, 13), (14, 15), (16, 17))

    def test_segment_components_and_coercion(self):
        self.assertEqual(self.start.p1.data, (0.0, 1.0))
        self.assertEqual(self.start.t1.data, (2.0, 3.0))
        self.assertEqual(self.start.p2.data, (4.0, 5.0))
        self.assertEqual(self.start.t2.data, (6.0, 7.0))
        self.assertIs(Segment.coerce(self.start), self.start)
        self.assertEqual(Segment.coerce([ (0, 1), (2, 3), (4, 5), (6, 7) ]).p2.data, (4.0, 5.0))
        self.assertEqual(Segment.coerce({"p1": (0, 1), "t1": (2, 3), "p2": (4, 5), "t2": (6, 7)}).t2.data, (6.0, 7.0))

    def test_segment_requires_four_vectors(self):
        for bad in ((), ((0, 0),), ((0, 0),) * 3, ((0, 0),) * 5):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                Segment.coerce(bad)

    def test_segment_xml_shape(self):
        element = self.start.to_xml_element(ET)
        self.assertEqual(element.tag, "segment")
        self.assertEqual([child.tag for child in element], ["p1", "t1", "p2", "t2"])
        self.assertEqual(element.find("p2/vector/x").text, "4")

    def test_segment_interpolates_each_vector(self):
        middle = Segment.as_kind().interpolate(self.start, self.end, 0.25)
        self.assertEqual(middle.p1.data, (2.5, 3.5))
        self.assertEqual(middle.t1.data, (4.5, 5.5))
        self.assertEqual(middle.p2.data, (6.5, 7.5))
        self.assertEqual(middle.t2.data, (8.5, 9.5))

    def test_segment_animated_interpolation(self):
        animated = Animated(Segment)
        animated.add_keyframe(0, self.start, after="linear")
        animated.add_keyframe(1, self.end, before="linear")
        middle = animated.at(0.5)
        self.assertEqual(middle.p1.data, (5.0, 6.0))
        self.assertEqual(middle.t2.data, (11.0, 12.0))


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
