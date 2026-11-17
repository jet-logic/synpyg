"""Review tests for ``synpyg.track.track`` and ``synpyg.track.action``.

Layout
------
* ``*Test`` classes without ``expectedFailure`` pin behaviour that works today.
* Tests marked ``@unittest.expectedFailure`` assert the DESIRED behaviour for a
  confirmed bug. The suite passes now; once a bug is fixed unittest reports an
  "unexpected success", which is the cue to delete the decorator.

Drop this file into ``tests/`` and run ``python -m unittest discover -s tests -t .``.
"""

import unittest
from xml.etree import ElementTree as ET

from synpyg.root import Root
from synpyg.track.action import Add, Par, ParE, Pass, Seq, To
from synpyg.track.track import Track
from synpyg.value import Real


class Recorder:
    """Stand-in for an Animated that just records ``add_waypoint`` calls."""

    def __init__(self):
        self.calls: list[tuple[float, object, dict]] = []

    def add_waypoint(self, time, value, **kwargs):
        self.calls.append((time, value, kwargs))
        return self

    @property
    def times(self) -> list[float]:
        return [c[0] for c in self.calls]


def waypoints(anim) -> list[tuple[float, float]]:
    """(time, value) pairs of a real ``Animated`` of Real values, time-ordered."""
    el = anim.to_xml_element(ET)
    return [
        (float(w.get("time").rstrip("s")), float(w.find("real").get("value")))
        for w in el
    ]


# --------------------------------------------------------------------------
# Behaviour that works today (regression guards)
# --------------------------------------------------------------------------


class TrackBasicsTest(unittest.TestCase):
    def test_advance_moves_time_and_chains(self):
        t = Track()
        self.assertIs(t.advance(1.5), t)
        self.assertEqual(t.current_time, 1.5)

    def test_advance_rejects_negative_nan_and_inf(self):
        for bad in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                Track().advance(bad)

    def test_sub_is_an_independent_copy(self):
        t = Track()
        s = t @ 2
        s << Pass(1)
        self.assertEqual(t.current_time, 0)
        self.assertEqual(s.current_time, 3.0)

    def test_pass_advances_time_without_emitting_waypoints(self):
        t = Track()
        r = Recorder()
        t << Pass(2) << To(r, 1, dur=1)
        self.assertEqual(r.times, [3.0])
        self.assertEqual(t.current_time, 3.0)


class ToTest(unittest.TestCase):
    def test_default_duration_comes_from_track_hint(self):
        t = Track(hint_dur=2)
        r = Recorder()
        t << To(r, 1)
        self.assertEqual(r.times, [2.0])
        self.assertEqual(t.current_time, 2.0)

    def test_explicit_duration_wins_over_hint(self):
        t = Track(hint_dur=2)
        r = Recorder()
        t << To(r, 1, dur=0.5)
        self.assertEqual(r.times, [0.5])

    def test_several_props_share_one_timing(self):
        t = Track()
        a, b = Recorder(), Recorder()
        t << To((a, b), 1, dur=2)
        self.assertEqual((a.times, b.times), ([2.0], [2.0]))
        self.assertEqual(t.current_time, 2.0)

    def test_extra_kwargs_reach_add_waypoint(self):
        t = Track()
        r = Recorder()
        t << To(r, 1, dur=1, before="clamped")
        self.assertEqual(r.calls[0][2]["before"], "clamped")

    def test_offset_track_places_waypoints_after_the_offset(self):
        r = Recorder()
        Track() @ 2 << To(r, 1, dur=1)
        self.assertEqual(r.times, [3.0])

    def test_add_accumulates_on_a_real_animated(self):
        a = Real.new_animated().add_waypoint(0, 1.0)
        Track() << Add(a, 2.0, dur=1)
        self.assertEqual(waypoints(a), [(0.0, 1.0), (1.0, 3.0)])


class SeqTest(unittest.TestCase):
    def test_plain_seq_runs_items_back_to_back(self):
        t = Track()
        a, b = Recorder(), Recorder()
        t << Seq(To(a, 1, dur=1), To(b, 1, dur=2))
        self.assertEqual((a.times, b.times), ([1.0], [3.0]))
        self.assertEqual(t.current_time, 3.0)

    def test_stagger_overlaps_items_when_last_item_is_longest(self):
        t = Track()
        a, b = Recorder(), Recorder()
        t << Seq(To(a, 1, dur=1), To(b, 1, dur=1), stagger=0.25)
        self.assertEqual((a.times, b.times), ([1.0], [1.25]))
        self.assertEqual(t.current_time, 1.25)

    def test_zero_stagger_starts_items_together(self):
        # 0 is falsy; make sure it is honoured rather than treated as "unset".
        t = Track()
        a, b = Recorder(), Recorder()
        t << Seq(To(a, 1, dur=1), To(b, 1, dur=1), stagger=0)
        self.assertEqual((a.times, b.times), ([1.0], [1.0]))
        self.assertEqual(t.current_time, 1.0)

    def test_delay_inserts_a_gap_between_items(self):
        t = Track()
        a, b = Recorder(), Recorder()
        t << Seq(To(a, 1, dur=1), To(b, 1, dur=1), delay=0.5)
        self.assertEqual((a.times, b.times), ([1.0], [2.5]))
        self.assertEqual(t.current_time, 2.5)

    def test_nested_seq_starts_where_previous_item_ended(self):
        t = Track()
        a, b = Recorder(), Recorder()
        t << Seq(To(a, 1, dur=1), Seq(To(b, 1, dur=1), Pass(1)))
        self.assertEqual((a.times, b.times), ([1.0], [2.0]))
        self.assertEqual(t.current_time, 3.0)


class ParTest(unittest.TestCase):
    def test_par_lasts_as_long_as_its_longest_item(self):
        t = Track()
        a, b = Recorder(), Recorder()
        t << Par(To(a, 1, dur=1), To(b, 1, dur=3))
        self.assertEqual((a.times, b.times), ([1.0], [3.0]))
        self.assertEqual(t.current_time, 3.0)

    def test_pare_right_aligns_item_ends(self):
        t = Track()
        a, b = Recorder(), Recorder()
        t << ParE(To(a, 1, dur=1), To(b, 1, dur=3))
        self.assertEqual((a.times, b.times), ([3.0], [3.0]))
        self.assertEqual(a.calls[0][2]["start"], 2.0)
        self.assertEqual(t.current_time, 3.0)


# --------------------------------------------------------------------------
# Confirmed bugs: tests assert the desired behaviour (expected to fail today)
# --------------------------------------------------------------------------


class SeqDurationTest(unittest.TestCase):
    """A Seq lasts until its LONGEST item ends (fixed; was: end of last item)."""

    def test_seq_stagger_duration_covers_longest_item(self):
        t = Track()
        a, b = Recorder(), Recorder()
        t << Seq(To(a, 1, dur=5), To(b, 1, dur=1), stagger=0.5)
        self.assertEqual(a.times, [5.0])
        self.assertEqual(t.current_time, 5.0)

    def test_seq_negative_delay_duration_covers_longest_item(self):
        t = Track()
        a, b = Recorder(), Recorder()
        t << Seq(To(a, 1, dur=5), To(b, 1, dur=1), delay=-4)
        self.assertEqual(a.times, [5.0])
        self.assertEqual(t.current_time, 5.0)

    def test_action_after_staggered_seq_starts_after_all_its_items(self):
        t = Track()
        a, b, c = Recorder(), Recorder(), Recorder()
        t << Seq(Seq(To(a, 1, dur=5), To(b, 1, dur=1), stagger=0.5), To(c, 1, dur=1))
        self.assertEqual(c.times, [6.0])


class ToStartBugTest(unittest.TestCase):
    """To() passes start=s to add_waypoint, but add_waypoint ignores it (TODO)."""

    # @unittest.expectedFailure
    def test_to_holds_previous_value_until_its_start_time(self):
        a = Real.new_animated().add_waypoint(0, 0.0)
        t = Track()
        t.advance(5)
        t <<= To(a, 1.0, dur=1)
        # The ramp must cover 5s..6s. Today only (0s, 0) and (6s, 1) exist, so
        # the value ramps over 0s..6s instead.
        self.assertIn((5.0, 0.0), waypoints(a))
        self.assertIn((6.0, 1.0), waypoints(a))


class DurationValidationBugTest(unittest.TestCase):
    """Negative / NaN durations are not validated; time can run backwards."""

    # @unittest.expectedFailure
    def test_negative_pass_duration_is_rejected(self):
        t = Track()
        t.advance(10)
        with self.assertRaises(ValueError):
            t << Pass(-3)  # today: silently rewinds current_time to 7

    # @unittest.expectedFailure
    def test_negative_to_duration_is_rejected(self):
        t = Track()
        t.advance(10)
        with self.assertRaises(ValueError):
            t << To(Recorder(), 1, dur=-1)  # today: waypoint at 9, time rewinds

    # @unittest.expectedFailure
    def test_nan_pass_duration_is_rejected(self):
        t = Track()
        with self.assertRaises(ValueError):
            t << Pass(float("nan"))  # today: silently a zero-length no-op

    # @unittest.expectedFailure
    def test_negative_track_hint_dur_is_rejected(self):
        with self.assertRaises(ValueError):
            Track(hint_dur=-1)  # today: every To() without dur rewinds time


class AssertAsValidationBugTest(unittest.TestCase):
    """Negative offsets are clamped to the track's base time, not to the Seq's
    own start, so nested items can begin before their Seq (and ``assert``
    statements that depend on this vanish under -O)."""

    # @unittest.expectedFailure
    def test_nested_seq_with_negative_delay_does_not_start_items_early(self):
        t = Track()
        a, b = Recorder(), Recorder()
        t << Seq(Pass(1), Seq(To(a, 1, dur=0.25), To(b, 1, dur=0.25), delay=-0.5))
        # the inner Seq starts at 1s; `b` must not start before that
        self.assertGreaterEqual(b.calls[0][2]["start"], 1.0)  # today: 0.75

    # @unittest.expectedFailure
    def test_pare_with_decimal_durations_does_not_assert(self):
        # 0.3 + 0.1 and 0.3 + 0.7 are not exactly representable, so the exact
        # float comparison `res.end == E` fails after the shift.
        t = Track()
        t.advance(0.3)
        a, b = Recorder(), Recorder()
        try:
            t << ParE(To(a, 1, dur=0.1), To(b, 1, dur=0.7))
        except AssertionError:
            self.fail("AssertionError (assert res.end == E) on decimal durations")
        self.assertAlmostEqual(a.times[0], b.times[0])


class EmptyContainerBugTest(unittest.TestCase):
    """Seq()/Par()/ParE() with no items hit ``assert head`` in llsup().

    Desired behaviour chosen here: a zero-length no-op (the usual result of
    ``Seq(*[... for x in xs])`` with an empty ``xs``). Raising ValueError
    would be a defensible alternative; AssertionError is not.
    """

    # @unittest.expectedFailure
    def test_empty_seq_is_a_noop(self):
        t = Track()
        t << Seq()
        self.assertEqual(t.current_time, 0)

    # @unittest.expectedFailure
    def test_empty_par_is_a_noop(self):
        t = Track()
        t << Par()
        self.assertEqual(t.current_time, 0)


class StaggerAndDelayBugTest(unittest.TestCase):
    # @unittest.expectedFailure
    def test_seq_rejects_stagger_and_delay_together(self):
        # today `delay` is silently ignored when `stagger` is also given
        with self.assertRaises(ValueError):
            Track() << Seq(Pass(1), Pass(1), stagger=0.25, delay=5)


class RootTrackBugTest(unittest.TestCase):
    """Adjacent to the requested scope (synpyg/root.py), but it makes the whole
    Track API unreachable from Root."""

    # @unittest.expectedFailure
    def test_root_offset_returns_a_usable_track(self):
        t = Root() @ 1  # today: AttributeError, RootTrack never runs Track.__init__
        self.assertEqual(t.current_time, 1.0)


if __name__ == "__main__":
    unittest.main()
