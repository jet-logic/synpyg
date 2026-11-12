from pathlib import Path
import tempfile
import unittest
from xml.etree import ElementTree as ET
from synpyg.animated import Waypoint
from synpyg.base import Property
from synpyg.canvas import Canvas
from synpyg.value import Color, Integer, Real, Vector


class Test(unittest.TestCase):
    def test_value(self):
        from synpyg.layer import SolidColorLayer

        s = SolidColorLayer()
        print(repr(s.amount))
        print(repr(s.blend_method))
        c = Color((1.0, 1.0, 1.0, 0.0))
        self.assertEqual(repr(c), "Color((1.0, 1.0, 1.0, 0.0))")

    # def test_property_isinstance(self):
    #     from synpyg.layer import SolidColorLayer, CircleLayer

    #     s = SolidColorLayer()
    #     c = CircleLayer()
    #     self.assertIsNot(s.z_depth, c.z_depth)
    #     self.assertIsNot(s.amount.value, c.amount.value)

    def test_dynamic_property(self):
        from synpyg.layer import SolidColorLayer

        s = SolidColorLayer()
        self.assertIsInstance(s.amount, Property)
        # assert isinstance(s.amount.value, Real)
        # self.assertEqual(s.amount.value.data, 1.0)
        self.assertIsInstance(s.blend_method, Property)
        # self.assertIsInstance(s.blend_method.value, Integer)
        # assert isinstance(s.blend_method.value, Integer)
        # self.assertIs(s.blend_method.value.data, 1)
        self.assertSequenceEqual(
            [k for k, v in s._enum_params()], ["amount", "blend_method"]
        )
        # s.flag = Property(Integer(67))  # type: ignore
        s.flag = Integer(67).as_prop()  # type: ignore

        self.assertSequenceEqual(
            [k for k, v in s._enum_params()], ["amount", "blend_method", "flag"]
        )

    def test_Waypoint(self):
        w = Waypoint()
        # w.before
        w.time = 4
        w.after = "qerreq"
        w.temporal_tension = 0.87
        w.value = Real(1.0)
        print({k: a.name for k, a in w._attrs.items()})
        self.assertSequenceEqual(
            sorted(w.__dict__.keys()), ["after", "temporal_tension", "time", "value"]
        )

        print(ET.tostring(w.to_xml_element(ET)))

    def test_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "test.sif"

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
            sol.set_params(color=(1, 0, 1, 1))
            self.assertIsInstance(sol.color.value, Color)

            g = root.add_group_layer()
            cir = g.add_circle_layer("MovingBall")
            cir.color.set_value([0, 0.8, 0.8, 1.0])
            cir.radius.set_value(1.2)

            mbl = g.add_motion_blur_layer("MotionBlur")
            mbl.set_params(subsample_start=0, subsample_end=1)
            mbl.aperture.set_value(0.75)
            mbl.subsampling_type.set_value(3)

            anim = cir.origin.as_animated()
            anim.add_waypoint(
                0, Vector([-6, 0]), before="clamped", after="clamped"
            ).add_waypoint(1, Vector([-6, 0])).add_waypoint(
                4, Vector([6, 0]), before="clamped", after="clamped"
            ).add_waypoint(
                5, Vector([6, 0]), before="clamped", after="clamped"
            )

            root.save_xml(out)
            self.assertTrue(out.is_file())

            # Sanity-check the serialized tree instead of trusting save_xml blindly.
            tree = ET.parse(out)
            canvas = tree.getroot()
            self.assertEqual(canvas.tag, "canvas")
            self.assertEqual(canvas.get("width"), "1920")
            self.assertEqual(canvas.get("fps"), "24.0")
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
