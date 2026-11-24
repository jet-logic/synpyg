import unittest
from xml.etree import ElementTree as ET

from synpyg.canvas import Canvas
from synpyg.layer import (
    ConicalGradientLayer,
    LinearGradientLayer,
    RadialGradientLayer,
    SpiralGradientLayer,
)
from synpyg.value import Gradient


def gradient():
    return [(0, (1, 0, 0, 1)), (1, (0, 0, 1, 1))]


class GradientLayerTest(unittest.TestCase):
    def test_linear_gradient_layer_xml(self):
        layer = LinearGradientLayer("linear")
        layer.p1 = (0, 0)
        layer.p2 = (4, 2)
        layer.gradient = gradient()
        layer.loop = False
        layer.zigzag = True
        root = layer.to_xml_element(ET)
        self.assertEqual(root.get("type"), "linear_gradient")
        self.assertEqual(root.find("param[@name='p1']/vector/x").text, "0")
        self.assertEqual(root.find("param[@name='p2']/vector/y").text, "2")
        self.assertEqual(len(root.findall("param[@name='gradient']/gradient/color")), 2)
        self.assertEqual(root.find("param[@name='zigzag']/bool").get("value"), "true")

    def test_radial_gradient_layer_xml(self):
        layer = RadialGradientLayer()
        layer.gradient = gradient()
        layer.center = (1, 2)
        layer.radius = 3
        layer.loop = True
        layer.zigzag = False
        root = layer.to_xml_element(ET)
        self.assertEqual(root.get("type"), "radial_gradient")
        self.assertIsNotNone(root.find("param[@name='center']/vector"))
        self.assertEqual(root.find("param[@name='radius']/real").get("value"), "3")

    def test_conical_gradient_layer_xml(self):
        layer = ConicalGradientLayer()
        layer.gradient = gradient()
        layer.center = (0, 0)
        layer.light_angle = 45
        layer.symmetric = True
        root = layer.to_xml_element(ET)
        self.assertEqual(root.get("type"), "conical_gradient")
        self.assertEqual(root.find("param[@name='light_angle']/angle").get("value"), "45")
        self.assertEqual(root.find("param[@name='symmetric']/bool").get("value"), "true")

    def test_spiral_gradient_layer_xml(self):
        layer = SpiralGradientLayer()
        layer.gradient = gradient()
        layer.center = (0, 0)
        layer.radius = 2
        layer.angle = 90
        layer.clockwise = False
        root = layer.to_xml_element(ET)
        self.assertEqual(root.get("type"), "spiral_gradient")
        self.assertEqual(root.find("param[@name='angle']/angle").get("value"), "90")
        self.assertEqual(root.find("param[@name='clockwise']/bool").get("value"), "false")

    def test_canvas_factories_insert_all_four_layer_types(self):
        canvas = Canvas()
        layers = [
            canvas.add_linear_gradient_layer(),
            canvas.add_radial_gradient_layer(),
            canvas.add_conical_gradient_layer(),
            canvas.add_spiral_gradient_layer(),
        ]
        self.assertEqual(
            [layer.layer_type for layer in layers],
            ["linear_gradient", "radial_gradient", "conical_gradient", "spiral_gradient"],
        )
        self.assertEqual([child for child in canvas], layers)

    def test_gradient_param_is_typed(self):
        layer = RadialGradientLayer()
        layer.gradient = gradient()
        self.assertIsInstance(layer.gradient.value, Gradient)
        with self.assertRaises(ValueError):
            layer.gradient = "not a gradient"


if __name__ == "__main__":
    unittest.main()
