import unittest
from xml.etree import ElementTree as ET

from synpyg.animated import Animated
from synpyg.canvas import Canvas
from synpyg.layer import CircleLayer
from synpyg.value import Real


class AssignGivenTest(unittest.TestCase):
    def test_skips_none_and_sets_the_rest(self):
        c = CircleLayer()
        self.assertIs(c._assign_given(desc="ball", group=None), c)
        self.assertEqual(c.desc, "ball")
        self.assertNotIn("group", c.__dict__)

    def test_none_is_not_the_same_as_assign(self):
        with self.assertRaises(ValueError):
            CircleLayer()._assign(desc=None)
        CircleLayer()._assign_given(desc=None)  # no error

    def test_unknown_names_are_rejected_even_when_none(self):
        with self.assertRaisesRegex(TypeError, "radiuss"):
            CircleLayer()._assign_given(radiuss=None)

    def test_unknown_name_sets_nothing(self):
        c = CircleLayer()
        with self.assertRaises(TypeError):
            c._assign_given(group="g", bogus=1)
        self.assertNotIn("group", c.__dict__)

    def test_invalid_values_are_still_rejected(self):
        with self.assertRaises(ValueError):
            CircleLayer()._assign_given(desc=3)

    def test_params_can_be_assigned_too(self):
        c = CircleLayer()._assign_given(radius=2, feather=None)
        self.assertEqual(c.radius.value.data, 2.0)
        self.assertFalse(c.feather.has_value)


class AnimatedInitTest(unittest.TestCase):
    def test_unset_arguments_stay_out_of_the_xml(self):
        el = Animated(Real).to_xml_element(ET)
        self.assertEqual(el.attrib, {"type": "real"})

    def test_given_arguments_are_assigned(self):
        a = Animated(Real, id="x", guid="g", interpolation="linear")
        self.assertEqual(
            a.to_xml_element(ET).attrib,
            {"type": "real", "id": "x", "guid": "g", "interpolation": "linear"},
        )

    def test_bad_interpolation_is_rejected(self):
        with self.assertRaises(ValueError):
            Animated(Real, interpolation="bogus")


class CanvasInitTest(unittest.TestCase):
    def test_optional_attributes_are_omitted_when_none(self):
        attrs = Canvas().to_xml_element(ET).attrib
        for name in ("begin-time", "end-time", "view-box"):
            self.assertNotIn(name, attrs)

    def test_frames_resolve_because_fps_is_set_first(self):
        c = Canvas(fps=24, begin_time="12f", end_time="48f", view_box=(0, 0, 4, 3))
        self.assertEqual((c.begin_time, c.end_time), (0.5, 2.0))
        self.assertEqual(c.view_box, (0.0, 0.0, 4.0, 3.0))


if __name__ == "__main__":
    unittest.main()
