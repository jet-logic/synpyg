import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from synpyg.animated import Waypoint
from synpyg.base import Property
from synpyg.canvas import Canvas
from synpyg.layer import SolidColorLayer
from synpyg.value import Boolean, Color, Integer, Real, String, Vector


class Test(unittest.TestCase):
    def test_value(self):
        c = Color((1.0, 1.0, 1.0, 0.0))
        self.assertEqual(repr(c), "Color((1.0, 1.0, 1.0, 0.0))")

    def test_dynamic_property(self):
        s = SolidColorLayer()
        self.assertIsInstance(s.amount, Property)
        self.assertIsInstance(s.blend_method, Property)
        self.assertSequenceEqual(
            [k for k, v in s._enum_params()], ["amount", "blend_method"]
        )
        s.flag = Integer(67).as_prop()  # type: ignore

        self.assertSequenceEqual(
            [k for k, v in s._enum_params()], ["amount", "blend_method", "flag"]
        )

    def test_dynamic_property_name(self):
        s = SolidColorLayer()
        s.flag = Integer(67).as_prop()
        el = s.to_xml_element(ET)
        self.assertEqual(el.find("param[@name='flag']/integer").get("value"), "67")

    def test_unnamed_property_rejected(self):
        with self.assertRaises(ValueError):
            Integer(1).as_prop().to_xml_element(ET)

    def test_no_exponent_or_float_noise(self):
        self.assertEqual(Real(1e-7).to_xml_element(ET).get("value"), "0.0000001")
        self.assertEqual(Real(0.1 + 0.2).to_xml_element(ET).get("value"), "0.3")
        with self.assertRaises(ValueError):
            Real(float("nan")).to_xml_element(ET)

    def test_constructors_validate(self):
        for bad in [
            lambda: Boolean(1),
            lambda: Integer(2.7),
            lambda: Integer(True),
            lambda: Real("abc"),
            lambda: Real(float("nan")),
            lambda: String(5),
        ]:
            with self.assertRaises(ValueError):
                bad()
        self.assertEqual(Integer(3.0).data, 3)
        self.assertEqual(Integer("3").data, 3)
        self.assertEqual(Real("1.5").data, 1.5)

    def test_Waypoint(self):
        w = Waypoint()
        w.time = 4
        w.before = "halt"
        w.temporal_tension = 0.87
        w.value = Real(1.0)

        self.assertSequenceEqual(
            sorted(w.__dict__.keys()), ["before", "temporal_tension", "time", "value"]
        )

    def test_write(self):
        if 1:
            out = Path(tempfile.gettempdir()) / "test.sif"

            root = Canvas(
                version="1.2",
                width=1920,
                height=1080,
                fps=24.000,
                begin_time="0f",
                end_time="5s",
                view_box="-10 5.625 10 -5.625",
            )

            sol = root.add_solid_color_layer("Background")
            self.assertEqual(sol.desc, "Background")
            sol._assign(color=(0.5, 1, 0, 1))
            self.assertIsInstance(sol.color.value, Color)

            g = root.add_group_layer()
            cir = g.add_circle_layer("MovingBall")
            cir.color.set_value([0, 0.8, 0.8, 1.0])
            cir.radius.set_value(1.2)

            mbl = g.add_motion_blur_layer("MotionBlur")
            mbl._assign(subsample_start=0, subsample_end=1)
            mbl.aperture.set_value(0.75)
            mbl.subsampling_type.set_value(3)

            anim = cir.origin.as_animated()
            anim.add_waypoint(
                0, Vector([-6, 0]), before="clamped", after="clamped"
            ).add_waypoint(1, Vector([-6, 0])).add_waypoint(
                4, Vector([6, 0]), before="clamped", after="clamped"
            ).add_waypoint(5, Vector([6, 0]), before="clamped", after="clamped")

            root.save_xml(out)
            self.assertTrue(out.is_file())

            # Sanity-check the serialized tree instead of trusting save_xml blindly.
            tree = ET.parse(out)
            canvas = tree.getroot()
            self.assertEqual(canvas.tag, "canvas")
            self.assertEqual(canvas.get("width"), "1920")
            self.assertEqual(canvas.get("fps"), "24")
            self.assertEqual(canvas.get("begin-time"), "0s")
            self.assertEqual(canvas.get("end-time"), "5s")
            self.assertEqual(canvas.get("view-box"), "-10 5.625 10 -5.625")

            layer_types = [el.get("type") for el in canvas.findall("layer")]
            self.assertEqual(layer_types, ["solid_color", "group"])

            # The animated origin on the circle should have produced waypoints.
            group = canvas.findall("layer")[1]
            circle = group.find(".//layer[@type='circle']")
            self.assertIsNotNone(circle)
            self.assertEqual(len(circle.findall(".//waypoint")), 4)  # type: ignore


if __name__ == "__main__":
    unittest.main()
