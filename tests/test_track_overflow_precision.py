import unittest

from synpyg.animated import Animated
from synpyg.track.action import ParE, To
from synpyg.track.track import Track
from synpyg.value import Real


class TrackFeedOverflowTests(unittest.TestCase):
    def test_finite_action_endpoint_overflow_is_rejected_before_finalizer(self):
        animated = Real.new_animated().add_keyframe(0, 0.0)
        track = Track(current_time=1e308)

        with self.assertRaises(ValueError):
            track << To(animated, 1.0, dur=1e308)

        self.assertEqual(track.current_time, 1e308)
        self.assertEqual(len(animated.waypoints), 1)

    def test_feed_rejects_overflow_in_track_time_before_finalizer(self):
        track = Track(current_time=1e308)
        called = []

        def resolver(start, base_frame, hint_dur):
            def finalize(track, start, end):
                called.append((start, end))

            # A valid finite action range whose duration overflows when added
            # to the track's current time.
            return 0.0, 1e308, finalize

        with self.assertRaises(ValueError):
            track.feed(resolver)

        self.assertEqual(track.current_time, 1e308)
        self.assertEqual(called, [])


class SameTimePrecisionTests(unittest.TestCase):
    def test_animated_keeps_distinct_large_timestamps(self):
        animated = Animated(Real)
        animated.add_keyframe(1e9, 1.0)
        later = 1e9 + 0.0005
        animated.add_keyframe(later, 2.0)

        self.assertEqual(len(animated.waypoints), 2)
        self.assertEqual([wp.time for wp in animated.waypoints], [1e9, later])

    def test_pare_aligns_endpoints_that_are_distinct_at_large_times(self):
        class Recorder:
            def __init__(self):
                self.calls = []

            def add_keyframe(self, time, value, **kwargs):
                self.calls.append((time, value, kwargs))

        short = Recorder()
        long = Recorder()
        start = 1e9
        track = Track(current_time=start)
        track << ParE(
            To(short, 1.0, dur=0.0005),
            To(long, 2.0, dur=0.001),
        )

        expected_end = start + 0.001
        self.assertEqual(short.calls[0][0], expected_end)
        self.assertEqual(long.calls[0][0], expected_end)
        self.assertEqual(short.calls[0][2]["start"], expected_end - 0.0005)
        self.assertEqual(track.current_time, expected_end)


if __name__ == "__main__":
    unittest.main()
