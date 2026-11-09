import unittest

from synpyg.base import Property
from synpyg.canvas import Canvas
from synpyg.value import Integer


class Test(unittest.TestCase):
    def test_value(self):
        from synpyg.layer import SolidColorLayer

        s = SolidColorLayer()
        print(repr(s.amount))
        print(repr(s.blend_method))

    def test_dynamic_property(self):
        from synpyg.layer import SolidColorLayer

        s = SolidColorLayer()
        self.assertIsInstance(s.amount, Property)
        print(s.amount)
        self.assertEqual(s.amount.value.value, 1.0)
        self.assertIsInstance(s.blend_method, Property)
        self.assertIsInstance(s.blend_method.value, Integer)
        self.assertIs(s.blend_method.value.value, 1)
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
        sol = root.add_solid_color_layer("Background")
        self.assertEqual(sol.desc, "Background")
        print(sol.color.value)
        sol.color.set_value((1, 0, 0, 1))
        print(sol.color.value)
        root.save_xml("/tmp/test.sif")


if __name__ == "__main__":
    unittest.main()
