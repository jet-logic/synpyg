import unittest

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
        s.flag = Property(Integer(67))  # type: ignore
        self.assertSequenceEqual(
            [k for k, v in s._enum_params()], ["amount", "blend_method", "flag"]
        )

    def test_write(self):
        root = Canvas(
            version="1.2",
            width=1920,
            height=1080,
            fps=24.000,
            start_time="0f",
            end_time="5s",
            view_box="-10 5.625 10 -5.625",
        )
        if sol := root.add_solid_color_layer("Background"):
            self.assertEqual(sol.desc, "Background")
            print("sol.color.value", sol.color.value)
            # sol.color.set_value((1, 0, 1, 1))
            sol.set_params(color=(1, 0, 1, 1))
            print("sol.color.value", sol.color.value)

        if g := root.add_group_layer():
            if cir := g.add_circle_layer("MovingBall"):
                cir.color.set_value([0, 0.8, 0.8, 1.0])
                cir.radius.set_value(1.2)
            if mbl := g.add_motion_blur_layer("MotionBlur"):
                mbl.set_params(subsample_start=0, subsample_end=1)
                mbl.aperture.set_value(0.75)
                mbl.subsampling_type.set_value(3)

            a = cir.origin.as_animated()
            a.add_waypoint(
                0, Vector([-6, 0]), before="clamped", after="clamped"
            ).add_waypoint(1, Vector([-6, 0])).add_waypoint(
                4, Vector([6, 0]), before="clamped", after="clamped"
            ).add_waypoint(
                5, Vector([6, 0]), before="clamped", after="clamped"
            )

        root.save_xml("/tmp/test.sif")


if __name__ == "__main__":
    unittest.main()
