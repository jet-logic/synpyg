import unittest
from xml.etree import ElementTree as ET
from synpyg.layer import Layer
from synpyg.animated import Animated
from synpyg.base import Param
from synpyg.value import Angle, Color, String, Vector


class StringAngleValueTest(unittest.TestCase):
    def test_string_constructs_with_data(self):
        s = String("hello")
        self.assertEqual(s.data, "hello")
        self.assertIsNone(s.id)
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
        self.assertEqual(a.to_xml_element(ET).attrib, {"value": "90.0"})

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
        a = Animated()
        a._type = String
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


if __name__ == "__main__":
    unittest.main()
