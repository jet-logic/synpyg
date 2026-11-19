"""Review findings for synpyg/track/track.py, synpyg/track/action.py and
synpyg/animated.py.

Run from the repository root:

    python -m unittest tests.test_review_findings        # if placed in tests/
    python -m unittest test_review_findings              # if repo root is on sys.path

Layout
------
* ``Confirmed bugs``      -- @expectedFailure; each asserts the DESIRED behaviour.
                             When a bug is fixed the test reports "unexpected
                             success", which is the cue to drop the decorator.
* ``Fixed oddities``      -- oddities that have been fixed; plain passing tests.
* ``Working behaviour``   -- plain passing tests that pin behaviour that works,
                             including documented design choices.

Every expectedFailure test was run with the decorator removed to check that it
fails for the reason described, not for an unrelated one.
"""

import ast
import math
import pathlib
import unittest
import xml.etree.ElementTree as ET
from unittest import expectedFailure

from synpyg import animated as animated_mod
from synpyg.track import timecmp
from synpyg.animated import Animated, Waypoint
from synpyg.track import action as action_mod
from synpyg.track.action import Add, Par, ParE, Pass, Seq, To
from synpyg.track.track import Track
from synpyg.value import Real, Vector

INF = math.inf


def to_xml(animated):
    return ET.tostring(animated.to_xml_element(ET), encoding="unicode")


def times(animated):
    return [w.time for w in animated.waypoints]


# ---------------------------------------------------------------------------
# Confirmed bugs
# ---------------------------------------------------------------------------


class ConfirmedBugs(unittest.TestCase):
    # B1 -- Track.feed promises atomicity but the finalizer is not atomic -------

    @expectedFailure
    def test_b1a_failed_to_on_several_props_leaves_every_prop_untouched(self):
        """To((real, vector), 5.0): the Vector rejects 5.0, but the Real has
        already received a waypoint by then."""
        real, vec = Animated(Real), Animated(Vector)
        track = Track()
        with self.assertRaises(ValueError):
            track << To((real, vec), 5.0, dur=1)
        self.assertEqual(len(real.waypoints), 0)
        self.assertEqual(len(vec.waypoints), 0)
        self.assertEqual(track.current_time, 0)

    @expectedFailure
    def test_b1b_failed_seq_does_not_leave_earlier_items_applied(self):
        """A later item failing at finalize time leaves earlier items' waypoints
        in place while the track clock has not advanced, so a retry duplicates
        them."""
        real, vec = Animated(Real), Animated(Vector)
        track = Track()
        with self.assertRaises(ValueError):
            track << Seq(To(real, 1.0), To(vec, 5.0))
        self.assertEqual(len(real.waypoints), 0)
        self.assertEqual(track.current_time, 0)

    def test_b1c_to_with_infinite_duration_fails_before_any_side_effect(self):
        """Durations are finite floats: To(dur=inf) is rejected when the
        action is written, before any sibling runs."""
        first, second = Animated(Real), Animated(Real)
        track = Track()
        with self.assertRaises(ValueError):
            track << Seq(To(first, 1.0), To(second, 2.0, dur=INF))
        self.assertEqual(len(first.waypoints), 0)
        self.assertEqual(track.current_time, 0)

    # B2 -- the synthetic "hold" waypoint copies id/guid ------------------------

    @expectedFailure
    def test_b2_hold_waypoint_does_not_duplicate_exported_id_or_guid(self):
        a = Animated(Real)
        a.add_waypoint(0, Real(1.0, id="keep", guid="G-1"))
        track = Track()
        track.advance(2)
        track << To(a, 5.0, dur=1)  # inserts a hold waypoint at t=2
        root = ET.fromstring(to_xml(a))
        ids = [e.get("id") for e in root.iter() if e.get("id")]
        guids = [e.get("guid") for e in root.iter() if e.get("guid")]
        self.assertEqual(len(ids), len(set(ids)), f"duplicate ids: {ids}")
        self.assertEqual(len(guids), len(set(guids)), f"duplicate guids: {guids}")

    # B3 -- infinite durations are rejected, so ParE never sees them ----------

    def test_b3_infinite_durations_are_rejected_up_front(self):
        for make in (
            lambda: ParE(Pass(INF), Pass(1)),
            lambda: ParE(Pass(INF), Pass(INF)),
        ):
            with self.subTest(make=make):
                with self.assertRaises(ValueError):
                    make()

    # B4 -- hand-built waypoint without a time ----------------------------------

    @expectedFailure
    def test_b4_timeless_waypoint_in_list_reports_value_error(self):
        """_check_waypoint validates value/kind but not time; the sort in
        _ordered_waypoints then raises a bare AttributeError. Every other
        bypass of add_waypoint is reported as ValueError/TypeError."""
        a = Animated(Real)
        w = Waypoint()
        w.value = Real(1.0)
        a.waypoints.append(w)
        with self.assertRaises(ValueError):
            a.to_xml_element(ET)


# ---------------------------------------------------------------------------
# Oddities with an unambiguous desired behaviour
# ---------------------------------------------------------------------------


class FixedOddities(unittest.TestCase):
    def test_o1_track_rejects_nonsensical_fps(self):
        """fps used to be stored unchecked."""
        for bad in (0, -5, float("nan"), INF):
            with self.subTest(fps=bad):
                with self.assertRaises((ValueError, TypeError)):
                    Track(fps=bad)

    def test_o2_to_with_non_animated_target_raises_type_error(self):
        """Used to surface as AttributeError from inside the finalizer."""
        with self.assertRaises(TypeError):
            Track() << To(Real(1.0), 2.0)
        with self.assertRaises(TypeError):  # already when the action is written
            To(Real(1.0), 2.0)
        with self.assertRaises(TypeError):  # one bad target in a list
            To([Animated(Real), "nope"], 2.0)

    def test_o3_reserved_kwargs_are_rejected_when_the_action_is_written(self):
        for kw in ("start", "time", "value"):
            with self.subTest(kw=kw):
                with self.assertRaises(ValueError):
                    To(Animated(Real), 1.0, **{kw: 0})
        with self.assertRaises(ValueError):
            Add(Animated(Real), 1.0, add=False)

    def test_o4_resolver_items_do_not_need_settable_attributes(self):
        """Seq/Par used to hang bookkeeping on the child's resolver function."""

        class Slotted:
            __slots__ = ()

            def __call__(self, start, base_time, hint_dur):
                return start, start + 1.0, lambda track, s, e: None

        track = Track()
        track << Seq(lambda t: Slotted(), lambda t: Slotted())
        self.assertEqual(track.current_time, 2.0)

    def test_o5_pass_none_uses_the_track_hint_like_to(self):
        track = Track(hint_dur=3)
        track << Pass(None)
        self.assertEqual(track.current_time, 3.0)
        track = Track(hint_dur=3)
        track << Pass()  # the default stays a fixed 1s
        self.assertEqual(track.current_time, 1.0)

    def test_o6_non_numeric_durations_and_offsets_get_a_clear_type_error(self):
        """Used to fail with "can't multiply sequence by non-int of type float"."""
        a = Animated(Real)
        for bad in ("1s", True, [1]):
            with self.subTest(dur=bad):
                with self.assertRaises(TypeError):
                    Track() << To(a, 1.0, dur=bad)
                with self.assertRaises(TypeError):
                    Track() << Seq(Pass(1), stagger=bad)
        with self.assertRaises(TypeError):
            Pass("1s")
        self.assertEqual(a.waypoints, [])

    def test_o7_repeated_steps_do_not_accumulate_float_noise(self):
        a = Animated(Real)
        track = Track()
        track << Seq(*[To(a, float(i), dur=0.1) for i in range(10)])
        self.assertEqual(times(a)[-1], 1.0)
        self.assertEqual(track.current_time, 1.0)
        for _ in range(10):
            track.advance(0.1)
        self.assertEqual(track.current_time, 2.0)

    def test_o10_track_package_imports_nothing_from_the_rest_of_the_library(self):
        """track/* must stay self-contained: stdlib and sibling modules only."""
        import synpyg.track as pkg

        base = pathlib.Path(next(iter(pkg.__path__)))
        files = sorted(base.glob("*.py"))
        self.assertTrue(files)
        for path in files:
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.ImportFrom):
                    mods = [node.module or ""]
                    ok = (node.level == 1) or (
                        node.level == 0 and not mods[0].startswith("synpyg")
                    )
                    if node.level == 0 and mods[0].startswith("synpyg.track"):
                        ok = True
                elif isinstance(node, ast.Import):
                    ok = all(not n.name.startswith("synpyg") for n in node.names)
                else:
                    continue
                with self.subTest(file=path.name, line=node.lineno):
                    self.assertTrue(ok, ast.dump(node))

    def test_o8_time_tolerance_is_defined_once(self):
        self.assertIs(animated_mod._same_time, timecmp.same_time)
        self.assertIs(action_mod._same_time, timecmp.same_time)

    def test_o9_seq_dur_is_a_hint_passed_down_to_items(self):
        """Pins the (previously misdocumented) behaviour of Seq(dur=...)."""
        a = Animated(Real)
        Track(hint_dur=1) << Seq(To(a, 1.0), dur=4)
        self.assertEqual(times(a), [4.0])


# ---------------------------------------------------------------------------
# Working behaviour worth pinning
# ---------------------------------------------------------------------------


class WorkingBehaviour(unittest.TestCase):
    def test_seq_runs_items_back_to_back_and_advances_track(self):
        a, b = Animated(Real), Animated(Real)
        track = Track()
        track << Seq(To(a, 1.0, dur=2), To(b, 2.0, dur=3))
        self.assertEqual(times(a), [2.0])
        self.assertEqual(times(b), [5.0])
        self.assertEqual(track.current_time, 5.0)

    def test_par_items_share_start_and_track_advances_by_longest(self):
        a, b = Animated(Real), Animated(Real)
        track = Track()
        track << Par(To(a, 1.0, dur=1), To(b, 1.0, dur=3))
        self.assertEqual(times(a), [1.0])
        self.assertEqual(times(b), [3.0])
        self.assertEqual(track.current_time, 3.0)

    def test_pare_right_aligns_item_ends(self):
        a, b = Animated(Real), Animated(Real)
        track = Track()
        track << ParE(To(a, 1.0, dur=1), To(b, 1.0, dur=3))
        self.assertEqual(times(a), [3.0])
        self.assertEqual(times(b), [3.0])

    def test_to_inserts_hold_waypoint_at_start_after_a_gap(self):
        a = Animated(Real)
        a.add_waypoint(0, 1.0)
        track = Track()
        track.advance(2)
        track << To(a, 5.0, dur=1)
        self.assertEqual(sorted(times(a)), [0.0, 2.0, 3.0])
        self.assertEqual(
            [w.value.data for w in sorted(a.waypoints, key=lambda w: w.time)],
            [1.0, 1.0, 5.0],
        )

    def test_to_adds_no_hold_when_a_waypoint_already_sits_at_start(self):
        a = Animated(Real)
        a.add_waypoint(0, 1.0)
        Track() << To(a, 5.0, dur=1)
        self.assertEqual(sorted(times(a)), [0.0, 1.0])

    def test_add_accumulates_and_merges_at_equal_time(self):
        a = Animated(Real)
        a.add_waypoint(0, 0.0)
        track = Track()
        track << Par(Add(a, 1.0, dur=1), Add(a, 1.0, dur=1))
        last = max(a.waypoints, key=lambda w: w.time)
        self.assertEqual(last.value.data, 2.0)
        self.assertEqual(len(a.waypoints), 2)

    def test_invalid_duration_is_rejected_before_anything_is_emitted(self):
        a = Animated(Real)
        track = Track()
        for bad in (-1, float("nan")):
            with self.subTest(dur=bad):
                with self.assertRaises(ValueError):
                    track << To(a, 1.0, dur=bad)
        self.assertEqual(a.waypoints, [])
        self.assertEqual(track.current_time, 0)

    def test_pass_infinity_is_rejected(self):
        track = Track()
        with self.assertRaises(ValueError):
            track << Pass(INF)
        self.assertEqual(track.current_time, 0)

    def test_sub_track_is_independent_of_its_parent(self):
        a = Animated(Real)
        track = Track()
        sub = track @ 2
        sub << To(a, 1.0, dur=1)
        self.assertEqual(times(a), [3.0])
        self.assertEqual(track.current_time, 0)

    def test_par_default_durations_depend_on_item_order(self):
        """Documented design: an item without ``dur`` takes the longest
        duration seen so far among earlier items."""
        for order, expected in (("apb", ([1.0], [3.0])), ("pab", ([3.0], [3.0]))):
            with self.subTest(order=order):
                a, b = Animated(Real), Animated(Real)
                items = {"a": To(a, 1.0), "p": Pass(3), "b": To(b, 1.0)}
                Track(hint_dur=1) << Par(*(items[k] for k in order))
                self.assertEqual((times(a), times(b)), expected)

    def test_hold_waypoint_takes_the_preceding_waypoints_own_value(self):
        """Documented limitation: not the interpolated value in effect."""
        a = Animated(Real)
        a.add_waypoint(0, 0.0)
        a.add_waypoint(2, 10.0)
        track = Track()
        track.advance(1)
        track << To(a, 99.0, dur=0.5)
        hold = [w for w in a.waypoints if w.time == 1.0][0]
        self.assertEqual(hold.value.data, 0.0)

    def test_resolver_fixes_its_duration_on_first_resolve(self):
        """Documented: ParE re-resolves items and relies on this."""
        resolve = To(Animated(Real), 1.0)(Track())
        self.assertEqual(resolve(0, 0, 1)[:2], (0, 1))
        self.assertEqual(resolve(5, 0, 9)[:2], (5, 6))

    def test_empty_seq_and_par_are_noops(self):
        track = Track()
        track << Seq() << Par() << ParE()
        self.assertEqual(track.current_time, 0)


if __name__ == "__main__":
    unittest.main()
