import unittest

from synpyg.canvas import Canvas
from synpyg.ref import Ref
from synpyg.value import Real


def animated(*times):
    a = Real.new_animated()
    for t in times:
        a.add_waypoint(t, 1.0)
    return a


class TimeRangeTests(unittest.TestCase):
    def test_empty_canvas_and_static_layers_have_no_range(self):
        c = Canvas()
        self.assertIsNone(c.time_range())
        c.add_circle_layer().radius = 1.0
        self.assertIsNone(c.time_range())

    def test_earliest_and_latest_are_by_time_not_insertion_order(self):
        c = Canvas()
        c.add_circle_layer().radius = animated(3, 1, 7, 2)
        self.assertEqual(c.time_range(), (1.0, 7.0))

    def test_single_waypoint(self):
        c = Canvas()
        c.add_circle_layer().radius = animated(2)
        self.assertEqual(c.time_range(), (2.0, 2.0))

    def test_spans_layers_params_and_nested_groups(self):
        c = Canvas()
        c.add_circle_layer().radius = animated(4, 5)
        outer = c.add_group_layer()
        outer.amount = animated(6)  # the group's own params count
        inner = outer.add_group_layer()
        inner.add_circle_layer().feather = animated(0.5, 9)
        self.assertEqual(c.time_range(), (0.5, 9.0))
        self.assertEqual(outer.time_range(), (0.5, 9.0))
        self.assertEqual(inner.time_range(), (0.5, 9.0))

    def test_group_range_ignores_siblings_outside_it(self):
        c = Canvas()
        c.add_circle_layer().radius = animated(100)
        g = c.add_group_layer()
        g.add_circle_layer().radius = animated(1, 2)
        self.assertEqual(g.time_range(), (1.0, 2.0))
        self.assertEqual(c.time_range(), (1.0, 100.0))

    def test_ref_to_an_exported_animation_is_followed(self):
        c = Canvas()
        shared = c.export("shared", animated(8, 12))
        c.add_circle_layer().radius = Ref(shared)
        c.add_circle_layer().feather = Ref(shared)  # reached twice, read once
        self.assertEqual(c.time_range(), (8.0, 12.0))

    def test_unreferenced_export_does_not_count(self):
        c = Canvas()
        c.export("unused", animated(50))
        c.add_circle_layer().radius = animated(1)
        self.assertEqual(c.time_range(), (1.0, 1.0))

    def test_ref_nested_in_a_waypoint_and_cycles_terminate(self):
        c = Canvas()
        a = c.export("a", animated(2))
        b = c.export("b", animated(20))
        a.add_waypoint(3, Ref(b))
        b.add_waypoint(21, Ref(a))  # a <-> b cycle
        c.add_circle_layer().radius = Ref(a)
        self.assertEqual(c.time_range(), (2.0, 21.0))

    def test_plain_use_string_is_skipped(self):
        c = Canvas()
        c.add_circle_layer().radius = Ref("other.sif#id")
        self.assertIsNone(c.time_range())


if __name__ == "__main__":
    unittest.main()
