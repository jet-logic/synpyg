import unittest
from xml.etree import ElementTree as ET

from synpyg.base import Property
from synpyg.canvas import Canvas
from synpyg.layer import GroupLayer
from synpyg.value import Value


class GroupCanvasValueTests(unittest.TestCase):
    def test_canvas_is_a_value_with_the_canvas_tag(self):
        canvas = Canvas()
        self.assertIsInstance(canvas, Value)
        self.assertEqual(Canvas.as_kind().tag, "canvas")
        self.assertEqual(canvas.to_xml_element(ET).tag, "canvas")

    def test_canvas_values_cannot_be_animated(self):
        with self.assertRaisesRegex(TypeError, "cannot be animated"):
            Canvas.new_animated()
        with self.assertRaisesRegex(TypeError, "cannot be animated"):
            Canvas.as_kind().new_animated()
        with self.assertRaisesRegex(TypeError, "cannot be animated"):
            GroupLayer().canvas.as_animated()

    def test_group_layer_has_a_typed_canvas_param_by_default(self):
        group = GroupLayer()
        self.assertIsInstance(group.canvas, Property)
        self.assertIsInstance(group.canvas.value, Canvas)
        self.assertEqual(group.canvas.name, "canvas")

    def test_inline_canvas_is_serialized_as_the_group_param_value(self):
        root = Canvas()
        group = root.add_group_layer("Inner")
        circle = group.add_circle_layer("Circle")
        circle.radius = 2.5

        xml = root.to_xml_element(ET)
        canvas = xml.find("layer/param[@name='canvas']/canvas")
        self.assertIsNotNone(canvas)
        self.assertEqual(canvas.find("layer").get("type"), "circle")  # type: ignore[union-attr]
        self.assertEqual(
            canvas.find("layer/param/real").get("value"), "2.5"  # type: ignore[union-attr]
        )

    def test_external_canvas_is_the_same_group_layer_with_canvas_use(self):
        root = Canvas()
        group = root.add_group_layer(canvas=Canvas(use="other.sif#canvas"))

        xml = root.to_xml_element(ET)
        canvas = xml.find("layer/param[@name='canvas']/canvas")
        self.assertIsInstance(group, GroupLayer)
        self.assertEqual(canvas.attrib, {"use": "other.sif#canvas"})  # type: ignore[union-attr]

    def test_a_use_string_coerces_to_external_canvas_value(self):
        root = Canvas()
        root.add_group_layer(canvas="other.sif#canvas")
        canvas = root.to_xml_element(ET).find("layer/param/canvas")
        self.assertEqual(canvas.get("use"), "other.sif#canvas")  # type: ignore[union-attr]

    def test_compatibility_helper_returns_a_group_layer(self):
        root = Canvas()
        group = root.add_external_canvas_layer("other.sif#canvas")
        self.assertIsInstance(group, GroupLayer)
        self.assertEqual(group.canvas.value.use, "other.sif#canvas")

    def test_grouping_methods_insert_into_the_canvas_value(self):
        root = Canvas()
        group = root.add_group_layer()
        circle = group.add_circle_layer()
        self.assertIs(circle._parent, group.canvas.value)
        self.assertEqual(list(group), [circle])
        self.assertEqual(list(group.children()), [circle])
        self.assertIs(group.first_child(), circle)

    def test_nested_canvas_animations_are_included_in_time_range(self):
        root = Canvas()
        group = root.add_group_layer()
        group.add_circle_layer().radius.as_animated().add_keyframe(2, 1.0).add_keyframe(5, 2.0)
        self.assertEqual(group.time_range(), (2.0, 5.0))
        self.assertEqual(root.time_range(), (2.0, 5.0))

    def test_external_canvas_cannot_also_contain_layers(self):
        root = Canvas()
        group = root.add_group_layer(canvas=Canvas(use="other.sif#canvas"))
        group.add_circle_layer()
        with self.assertRaisesRegex(ValueError, "cannot contain layers"):
            root.to_xml_element(ET)

    def test_defs_inside_a_group_canvas_are_rejected_explicitly(self):
        root = Canvas()
        group = root.add_group_layer()
        group.canvas.value.export("local", Canvas())
        with self.assertRaisesRegex(ValueError, "defs inside a group canvas"):
            root.to_xml_element(ET)


if __name__ == "__main__":
    unittest.main()
