import unittest
from synpyg.track.track import Track
from synpyg.track.action import Par, ParE, Seq, To


class MockProp:
    """A mock property that records waypoints added by To/ToA."""

    def __init__(self):
        self.waypoints = []

    def add_waypoint(self, time, value, start=None, **kwargs):
        self.waypoints.append((start, time, value))


class TestTrackBugs(unittest.TestCase):

    # @unittest.expectedFailure
    def test_par_respects_user_dur(self):
        """ParA ignores user-provided dur and uses 10% of it as a hint."""
        t = Track(hint_dur=1.0)
        p = MockProp()
        # We want the parallel group to take 10 seconds.
        # The child has dur=None, so it should use the hint_dur provided by Par.
        # But ParA multiplies dur by 0.10, so the child gets 1.0.
        action = Par(To(p, 1, dur=None), dur=10.0)
        t << action

        # The child should have received hint_dur=10.0, so it ends at 10.0.
        self.assertEqual(len(p.waypoints), 1)
        start, end, val = p.waypoints[0]
        self.assertEqual(end, 10.0)

    # @unittest.expectedFailure
    def test_advance_error_message_and_limits(self):
        """track.advance has a typo and an arbitrary hard limit."""
        t = Track()

        # Test typo
        try:
            t.advance(-1)
            self.fail("Should have raised ValueError")
        except ValueError as e:
            self.assertIn("Invalid", str(e))  # Fails because of "Invalide"

        # Test arbitrary limit
        # This should be valid for a float-based time system
        t.advance(3000000000.0)  # 2^31 + something
        self.assertEqual(t.current_time, 3000000000.0)

    # --- Passing tests to prevent regressions ---

    def test_seq_basic_functionality(self):
        """Seq correctly chains actions sequentially."""
        t = Track(hint_dur=2.0)
        p1 = MockProp()
        p2 = MockProp()

        action = Seq(To(p1, 1, dur=2.0), To(p2, 2, dur=3.0))
        t << action

        self.assertEqual(len(p1.waypoints), 1)
        self.assertEqual(p1.waypoints[0][1], 2.0)  # ends at 2.0

        self.assertEqual(len(p2.waypoints), 1)
        self.assertEqual(p2.waypoints[0][0], 2.0)  # starts at 2.0
        self.assertEqual(p2.waypoints[0][1], 5.0)  # ends at 5.0

    def test_par_basic_functionality(self):
        """Par correctly runs actions in parallel."""
        t = Track(hint_dur=1.0)
        p1 = MockProp()
        p2 = MockProp()

        action = Par(To(p1, 1, dur=2.0), To(p2, 2, dur=3.0))
        t << action

        self.assertEqual(p1.waypoints[0][1], 2.0)
        self.assertEqual(p2.waypoints[0][1], 3.0)

    def test_to_with_explicit_dur(self):
        """To respects explicit dur over hint_dur."""
        t = Track(hint_dur=5.0)
        p = MockProp()

        action = To(p, 1, dur=2.0)
        t << action

        self.assertEqual(p.waypoints[0][1], 2.0)


if __name__ == "__main__":
    unittest.main()
