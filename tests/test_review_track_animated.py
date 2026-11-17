"""Regression tests for the reviewed track/action/animation code.

Confirmed bugs use expectedFailure so the suite passes on the current source,
and unittest reports an unexpected success once the corresponding fix lands.
"""

import unittest
from xml.etree import ElementTree as ET

from synpyg.animated import Animated
from synpyg.track.action import Add, ParE, Pass, Seq, To
from synpyg.track.track import Track
from synpyg.value import Real


class TrackTimeValidationTests(unittest.TestCase):
    def test_constructor_rejects_negative_or_non_finite_initial_time(self):
        for value in (-1.0, float("nan"), float("inf"), -float("inf")):
            with self.subTest(current_time=value):
                with self.assertRaises(ValueError):
                    Track(current_time=value)

    def test_constructor_accepts_large_finite_initial_time(self):
        track = Track(current_time=2**31)
        self.assertEqual(track.current_time, 2**31)

    def test_advance_rejects_negative_or_non_finite_delta(self):
        for value in (-1.0, float("nan"), float("inf"), -float("inf")):
            with self.subTest(delta=value):
                with self.assertRaises(ValueError):
                    Track().advance(value)

    def test_advance_accepts_large_finite_result(self):
        track = Track(current_time=1.0)
        track.advance(2**31 - 1)
        self.assertEqual(track.current_time, 2**31)

    def test_advance_rejects_overflow_without_mutating_track(self):
        track = Track(current_time=float.fromhex("0x1.fffffffffffffp+1023"))
        with self.assertRaises(ValueError):
            track.advance(track.current_time)
        self.assertEqual(track.current_time, float.fromhex("0x1.fffffffffffffp+1023"))


class SequenceValidationTests(unittest.TestCase):
    @unittest.expectedFailure
    def test_non_finite_stagger_and_delay_fail_before_side_effects(self):
        for option in ("stagger", "delay"):
            for value in (float("nan"), float("inf"), -float("inf")):
                with self.subTest(option=option, value=value):
                    first = Real.new_animated().add_waypoint(0, 0.0)
                    second = Real.new_animated().add_waypoint(0, 0.0)
                    with self.assertRaises(ValueError):
                        Track() << Seq(
                            To(first, 1.0, dur=1.0),
                            To(second, 1.0, dur=1.0),
                            **{option: value},
                        )
                    self.assertEqual(len(first.waypoints), 1)
                    self.assertEqual(len(second.waypoints), 1)


class AnimatedStartTimeTests(unittest.TestCase):
    @unittest.expectedFailure
    def test_to_holds_previous_value_until_its_start_time(self):
        animated = Real.new_animated().add_waypoint(0, 0.0)
        track = Track()
        track.advance(5.0)
        track << To(animated, 1.0, dur=1.0)

        xml = animated.to_xml_element(ET)
        points = [
            (float(node.get("time")[:-1]), float(node.find("real").get("value")))
            for node in xml
        ]
        self.assertEqual(points, [(0.0, 0.0), (5.0, 0.0), (6.0, 1.0)])


class WorkingBehaviourTests(unittest.TestCase):
    def test_pass_advances_track_without_creating_waypoints(self):
        track = Track()
        track << Pass(2.5)
        self.assertEqual(track.current_time, 2.5)

    def test_to_uses_track_hint_duration(self):
        animated = Real.new_animated()
        track = Track(hint_dur=2.0)
        track << To(animated, 3.0)
        self.assertEqual(animated.waypoints[-1].time, 2.0)
        self.assertEqual(animated.waypoints[-1].value.data, 3.0)

    def test_add_accumulates_on_existing_animated_value(self):
        animated = Real.new_animated().add_waypoint(0, 2.0)
        Track() << Add(animated, 3.0, dur=1.0)
        self.assertEqual(animated.waypoints[-1].time, 1.0)
        self.assertEqual(animated.waypoints[-1].value.data, 5.0)

    def test_pare_aligns_decimal_duration_endpoints(self):
        first = Real.new_animated()
        second = Real.new_animated()
        track = Track()
        track << ParE(To(first, 1.0, dur=0.1), To(second, 2.0, dur=0.7))
        self.assertAlmostEqual(first.waypoints[-1].time, 0.7)
        self.assertAlmostEqual(second.waypoints[-1].time, 0.7)
        self.assertAlmostEqual(track.current_time, 0.7)

    def test_waypoint_order_is_stable_for_equal_times(self):
        animated = Animated(Real)
        animated.add_waypoint(1.0, 1.0).add_waypoint(1.0, 2.0)
        values = [
            float(node.find("real").get("value"))
            for node in animated.to_xml_element(ET)
        ]
        self.assertEqual(values, [1.0, 2.0])


if __name__ == "__main__":
    unittest.main()
