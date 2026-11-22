import unittest

from synpyg.animated import Animated
from synpyg.ref import Ref
from synpyg.value import Boolean, Integer, Real, String, Vector


class AnimatedAtTest(unittest.TestCase):
    def test_empty_animation_cannot_be_evaluated(self):
        with self.assertRaisesRegex(ValueError, "no waypoints"):
            Animated(Real).at(0)

    def test_one_waypoint_is_held_for_all_times(self):
        a = Animated(Real).add_keyframe(2, 7)
        for t in (-10, 2, 10):
            with self.subTest(time=t):
                self.assertEqual(a.at(t).data, 7.0)

    def test_holds_endpoints_outside_range(self):
        a = Animated(Real)
        a.add_keyframe(1, 10, after="linear")
        a.add_keyframe(3, 30, before="linear")
        self.assertEqual(a.at(-1).data, 10.0)
        self.assertEqual(a.at(4).data, 30.0)

    def test_exact_waypoint_returns_exact_value(self):
        a = Animated(Real).add_keyframe(0, 1, after="linear")
        a.add_keyframe(1, 4, before="linear")
        self.assertEqual(a.at(1).data, 4.0)

    def test_linear_segment_uses_both_waypoint_sides(self):
        a = Animated(Real).add_keyframe(0, 2, after="linear")
        a.add_keyframe(4, 10, before="linear")
        self.assertEqual(a.at(1).data, 4.0)

    def test_constant_on_either_side_holds_left_value(self):
        for options in ({"after": "constant"}, {"before": "constant"}):
            a = Animated(Real).add_keyframe(0, 2, after="linear")
            a.add_keyframe(4, 10, before="linear")
            (
                a.waypoints[0]._assign(**options)
                if "after" in options
                else a.waypoints[1]._assign(**options)
            )
            self.assertEqual(a.at(2).data, 2.0)

    def test_ease_has_zero_tangent_at_waypoint(self):
        a = Animated(Real).add_keyframe(0, 0, after="ease")
        a.add_keyframe(1, 10, before="linear")
        self.assertAlmostEqual(a.at(0.25).data, 1.09375)

    def test_auto_tcb_uses_neighboring_waypoints(self):
        a = Animated(Real).add_keyframe(0, 0)
        a.add_keyframe(1, 10)
        a.add_keyframe(2, 10)
        self.assertGreater(a.at(0.5).data, 5.0)

    def test_clamped_does_not_overshoot_neighboring_values(self):
        a = Animated(Real).add_keyframe(0, 0, after="linear")
        a.add_keyframe(1, 10, before="clamped", after="clamped")
        a.add_keyframe(2, 10, before="linear")
        self.assertLessEqual(a.at(0.75).data, 10.0)
        self.assertGreaterEqual(a.at(0.75).data, 0.0)

    def test_vector_values_interpolate_componentwise(self):
        a = Animated(Vector).add_keyframe(0, (0, 2), after="linear")
        a.add_keyframe(2, (4, 6), before="linear")
        self.assertEqual(a.at(1).data, (2.0, 4.0))

    def test_integer_values_are_rounded_to_integer(self):
        a = Animated(Integer).add_keyframe(0, 0, after="linear")
        a.add_keyframe(2, 3, before="linear")
        self.assertEqual(a.at(1).data, 2)

    def test_boolean_and_string_are_discrete(self):
        b = Animated(Boolean).add_keyframe(0, False, after="linear")
        b.add_keyframe(1, True, before="linear")
        self.assertIs(b.at(0.999).data, False)
        self.assertIs(b.at(1).data, True)
        s = Animated(String).add_keyframe(0, "old", after="linear")
        s.add_keyframe(1, "new", before="linear")
        self.assertEqual(s.at(0.999).data, "old")
        self.assertEqual(s.at(1).data, "new")

    def test_temporal_tension_changes_time_mapping(self):
        a = Animated(Real).add_keyframe(0, 0, after="linear", temporal_tension=0.8)
        a.add_keyframe(1, 10, before="linear", temporal_tension=0.0)
        self.assertGreater(a.at(0.5).data, 5.0)

    def test_ref_to_value_and_animated_are_evaluated(self):
        base = Real(5)
        a = Animated(Real).add_keyframe(0, Ref(base))
        self.assertEqual(a.at(3).data, 5.0)
        source = Animated(Real).add_keyframe(0, 2, after="linear")
        source.add_keyframe(2, 6, before="linear")
        linked = Animated(Real).add_keyframe(0, Ref(source))
        self.assertEqual(linked.at(1).data, 4.0)

    def test_unresolved_and_cyclic_refs_raise(self):
        a = Animated(Real).add_keyframe(0, Ref("external-id"))
        with self.assertRaisesRegex(ValueError, "unresolved reference"):
            a.at(0)
        cyclic_a, cyclic_b = Animated(Real), Animated(Real)
        from synpyg.animated import Waypoint

        wa = Waypoint()._assign(time=0)
        wb = Waypoint()._assign(time=0)
        wa.value, wb.value = Ref(cyclic_b), Ref(cyclic_a)
        cyclic_a.waypoints.append(wa)
        cyclic_b.waypoints.append(wb)
        with self.assertRaisesRegex(ValueError, "cyclic"):
            cyclic_a.at(0)

    def test_waypoints_are_evaluated_in_time_order(self):
        a = Animated(Real).add_keyframe(2, 20, after="linear")
        a.add_keyframe(0, 0)
        a.add_keyframe(4, 40, before="linear")
        self.assertEqual(a.at(3).data, 30.0)


if __name__ == "__main__":
    unittest.main()
