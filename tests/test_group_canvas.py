import unittest
from xml.etree import ElementTree as ET

from synpyg.base import Property
from synpyg.canvas import Canvas
from synpyg.layer import CircleLayer, GroupLayer, Layer, RectangleLayer
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

    def test_enum_layer_type_searches_descendants_in_depth_first_order(self):
        root = Canvas()
        first_circle = root.add_circle_layer("First circle")
        group = root.add_group_layer("Group")
        group_circle = group.add_circle_layer("Group circle")
        inner_group = group.add_group_layer("Inner group")
        inner_rectangle = inner_group.add_rectangle_layer("Inner rectangle")
        group_rectangle = group.add_rectangle_layer("Group rectangle")
        last_circle = root.add_circle_layer("Last circle")

        self.assertEqual(
            list(root.enum_layer_type(CircleLayer)),
            [first_circle, group_circle, last_circle],
        )
        self.assertEqual(
            list(root.enum_layer_type(RectangleLayer)),
            [inner_rectangle, group_rectangle],
        )
        self.assertEqual(list(root.enum_layer_type(GroupLayer)), [group, inner_group])
        self.assertEqual(
            list(root.enum_layer_type(Layer)),
            [
                first_circle,
                group,
                group_circle,
                inner_group,
                inner_rectangle,
                group_rectangle,
                last_circle,
            ],
        )

    def test_enum_layer_type_does_not_search_from_the_group_itself(self):
        group = Canvas().add_group_layer("Group")
        child = group.add_circle_layer("Child")

        self.assertEqual(list(group.enum_layer_type(GroupLayer)), [])
        self.assertEqual(list(group.enum_layer_type(CircleLayer)), [child])

    def test_find_layer_by_index_uses_filtered_depth_first_order(self):
        root = Canvas()
        first = root.add_circle_layer("First")
        group = root.add_group_layer("Group")
        nested = group.add_circle_layer("Nested")
        root.add_rectangle_layer("Rectangle")

        self.assertIs(root.find_layer(0, CircleLayer), first)
        self.assertIs(root.find_layer(1, CircleLayer), nested)

    def test_find_layer_by_desc_searches_depth_first_and_matches_exactly(self):
        root = Canvas()
        root.add_circle_layer("Needle")
        group = root.add_group_layer("Group")
        nested = group.add_circle_layer("Nested needle")
        root.add_circle_layer("needle")

        self.assertIs(root.find_layer("Nested needle", CircleLayer), nested)
        self.assertEqual(root.find_layer("Needle", CircleLayer).desc, "Needle")
        self.assertEqual(root.find_layer("needle", CircleLayer).desc, "needle")

    def test_find_layer_by_duplicate_desc_returns_first_match(self):
        root = Canvas()
        first = root.add_circle_layer("Duplicate")
        root.add_group_layer().add_circle_layer("Duplicate")

        self.assertIs(root.find_layer("Duplicate", CircleLayer), first)

    def test_find_layer_supports_default_for_both_lookup_modes(self):
        root = Canvas()
        fallback = CircleLayer("Fallback")

        self.assertIs(root.find_layer(0, CircleLayer, default=fallback), fallback)
        self.assertIs(
            root.find_layer("Missing", CircleLayer, default=fallback), fallback
        )

    def test_find_layer_validates_integer_indexes(self):
        root = Canvas()
        with self.assertRaises(TypeError):
            root.find_layer(1.5, CircleLayer)
        with self.assertRaises(TypeError):
            root.find_layer(True, CircleLayer)
        with self.assertRaises(IndexError):
            root.find_layer(-1, CircleLayer)

    def test_find_layer_raises_meaningful_errors_when_not_found(self):
        root = Canvas()
        with self.assertRaises(IndexError):
            root.find_layer(0, CircleLayer)
        with self.assertRaises(LookupError):
            root.find_layer("Missing", CircleLayer)

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
