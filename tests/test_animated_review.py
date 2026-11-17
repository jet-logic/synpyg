"""Review tests for synpyg/animated.py.

Layout
------
* ``@expectedFailure`` tests assert the DESIRED behaviour of a confirmed
  issue. The suite passes today; when a fix lands the test reports an
  "unexpected success" so the decorator can be removed.
* Plain tests pin behaviour that works today, so fixes cannot regress it.

Run from the project root (the directory containing ``synpyg/``)::

    python -m unittest test_animated_review -v
"""

import unittest
from unittest import expectedFailure
from xml.etree import ElementTree as ET

from synpyg.animated import Animated, Waypoint
from synpyg.canvas import Canvas
from synpyg.ref import Ref
from synpyg.value import Real, Value, Vector


def xml(node) -> ET.Element:
    return node.to_xml_element(ET)


def pairs(anim: Animated):
    """(time, data) of each waypoint in insertion order."""
    return [(w.time, w.value.data) for w in anim.waypoints]


# ---------------------------------------------------------------------------
# Confirmed bugs (expected failures; fixed ones have no decorator)
# ---------------------------------------------------------------------------


class RefCycleBugs(unittest.TestCase):
    """BUG 1 (fixed): waypoint Refs could form cycles that serialized silently."""

    def test_self_reference_rejected_at_add_waypoint(self):
        a = Animated(Real, id="x")
        with self.assertRaises(ValueError):
            a.add_waypoint(0, Ref(a))

    def test_indirect_reference_cycle_rejected_on_serialize(self):
        # a -> b -> a. Not detectable at add time (ids are resolved lazily),
        # so it has to be caught when the canvas is serialized.
        c = Canvas()
        a = c.export("a", Animated(Real))
        b = c.export("b", Animated(Real))
        a.add_waypoint(0, Ref(b))
        b.add_waypoint(0, Ref(a))
        with self.assertRaises(ValueError):
            xml(c)


    def test_self_reference_set_directly_rejected_on_serialize(self):
        a = Animated(Real, id="x")
        w = Waypoint()
        w.time = 0
        w.value = Ref(a)  # bypasses add_waypoint
        a.waypoints.append(w)
        with self.assertRaisesRegex(ValueError, "itself"):
            xml(a)

    def test_cycle_error_names_the_path(self):
        c = Canvas()
        a = c.export("a", Animated(Real))
        b = c.export("b", Animated(Real))
        d = c.export("d", Animated(Real))
        a.add_waypoint(0, Ref(b))
        b.add_waypoint(0, Ref(d))
        d.add_waypoint(0, Ref(b))
        with self.assertRaisesRegex(ValueError, "b -> d -> b"):
            xml(c)

    def test_self_cycle_in_canvas_is_rejected(self):
        c = Canvas()
        a = c.export("a", Animated(Real))
        a.waypoints.append(Waypoint()._assign(time=0))
        a.waypoints[0].value = Ref(a)
        with self.assertRaises(ValueError):
            xml(c)

    def test_acyclic_references_still_serialize(self):
        c = Canvas()
        base = c.export("base", Animated(Real).add_waypoint(0, 1))
        mid = c.export("mid", Animated(Real).add_waypoint(0, Ref(base)))
        top = c.export("top", Animated(Real).add_waypoint(0, Ref(mid)))
        top.add_waypoint(1, Ref(base))  # diamond, not a cycle
        uses = [w.get("use") for w in xml(c).iter("waypoint")]
        self.assertEqual(sorted(u for u in uses if u), ["base", "base", "mid"])

    def test_long_reference_chain_does_not_hit_recursion_limit(self):
        c = Canvas()
        prev = c.export("n0", Animated(Real).add_waypoint(0, 1))
        for i in range(1, 3000):
            prev = c.export(f"n{i}", Animated(Real).add_waypoint(0, Ref(prev)))
        xml(c)


class AddRelativeBug(unittest.TestCase):
    """BUG 2 (fixed): ``add=True`` is relative to the latest waypoint in time."""

    def test_add_is_relative_to_latest_waypoint_in_time(self):
        a = Animated(Real)
        a.add_waypoint(5, 10)
        a.add_waypoint(1, 1)  # inserted later, but earlier in time
        a.add_waypoint(7, 1, add=True)  # previous in time is the 5s waypoint
        self.assertEqual(a.waypoints[-1].value.data, 11.0)  # 10 + 1, not 1 + 1

    def test_incremental_check_uses_latest_time_not_last_inserted(self):
        a = Animated(Real)
        a.add_waypoint(5, 10)
        a.add_waypoint(1, 1)
        # 3s is before the 5s waypoint, so it is not incremental.
        with self.assertRaises(ValueError):
            a.add_waypoint(3, 1, add=True)


class EmptyIdBug(unittest.TestCase):
    """BUG 4 (fixed): ``id=""`` was written out as ``id=""`` (Value skips empty ids)."""

    def test_empty_id_is_not_serialized(self):
        self.assertNotIn("id", xml(Animated(Real, id="")).attrib)


class BypassingValidationBugs(unittest.TestCase):
    """BUG 4: only ``add_waypoint`` validates; direct use of the public
    ``waypoints`` list / ``Waypoint.value`` is accepted and serialized."""

    @expectedFailure
    def test_wrong_kind_waypoint_rejected_on_serialize(self):
        a = Animated(Vector)
        w = Waypoint()
        w.time = 0
        w.value = Real(1)  # a <real> inside <animated type="vector">
        a.waypoints.append(w)
        with self.assertRaises(ValueError):
            xml(a)

    @expectedFailure
    def test_non_value_waypoint_reports_value_error_not_attribute_error(self):
        w = Waypoint()
        w.time = 0
        w.value = 5
        with self.assertRaises((ValueError, TypeError)):
            xml(w)


# ---------------------------------------------------------------------------
# Oddities (also expected failures: they assert the behaviour I'd suggest)
# ---------------------------------------------------------------------------


class Oddities(unittest.TestCase):
    def test_untaggable_kind_raises_type_error(self):
        # NotImplementedError means "abstract method"; this is a bad argument.
        with self.assertRaises(TypeError):
            Animated(Value)

    @expectedFailure
    def test_add_waypoint_none_kwarg_means_unset(self):
        # Animated(...) already treats None as "leave unset".
        a = Animated(Real).add_waypoint(0, 1, before=None)
        self.assertNotIn("before", xml(a)[0].attrib)

    @expectedFailure
    def test_float_noise_does_not_break_incremental_check(self):
        a = Animated(Real)
        a.add_waypoint(0.1 + 0.2, 1)  # 0.30000000000000004
        a.add_waypoint(0.3, 2, add=True)  # same instant, up to rounding

    @expectedFailure
    def test_repr_is_informative(self):
        self.assertIn("Real", repr(Animated(Real)))
        self.assertIn("time", repr(Waypoint()._assign(time=1)))

    def test_no_previous_waypoint_error_is_not_chained(self):
        try:
            Animated(Real).add_waypoint(0, 1, add=True)
        except ValueError as e:
            self.assertIsNone(e.__context__)  # currently chained to IndexError


# ---------------------------------------------------------------------------
# Behaviour that works today (regression guards)
# ---------------------------------------------------------------------------


class WorkingBehaviour(unittest.TestCase):
    def test_add_waypoint_chains(self):
        a = Animated(Real)
        self.assertIs(a.add_waypoint(0, 1), a)

    def test_add_accumulates_in_time_order(self):
        a = Animated(Real).add_waypoint(0, 1)
        a.add_waypoint(1, 2, add=True).add_waypoint(2, 3, add=True)
        self.assertEqual(pairs(a), [(0.0, 1.0), (1.0, 3.0), (2.0, 6.0)])

    def test_add_at_same_time_merges_into_last_waypoint(self):
        a = Animated(Real).add_waypoint(1, 5, before="linear")
        a.add_waypoint(1, 2, add=True, after="halt")
        self.assertEqual(len(a.waypoints), 1)
        w = a.waypoints[0]
        self.assertEqual((w.time, w.value.data), (1.0, 7.0))
        self.assertEqual((w.before, w.after), ("linear", "halt"))

    def test_add_before_last_time_is_rejected(self):
        a = Animated(Real).add_waypoint(5, 10)
        with self.assertRaisesRegex(ValueError, "incremental"):
            a.add_waypoint(3, 1, add=True)

    def test_add_without_previous_waypoint_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "No previous waypoint"):
            Animated(Real).add_waypoint(0, 1, add=True)

    def test_add_with_ref_is_rejected_and_leaves_list_unchanged(self):
        a = Animated(Real).add_waypoint(0, 1)
        with self.assertRaises(ValueError):
            a.add_waypoint(1, Ref(Real(2, id="r")), add=True)
        self.assertEqual(pairs(a), [(0.0, 1.0)])

    def test_failed_add_waypoint_leaves_state_unchanged(self):
        a = Animated(Real).add_waypoint(1, 5)
        for kwargs in ({"bogus": 1}, {"before": "nope"}):
            for t in (1, 2):  # 1 hits the merge path, 2 the append path
                with self.subTest(kwargs=kwargs, t=t):
                    with self.assertRaises((TypeError, ValueError)):
                        a.add_waypoint(t, 1, add=True, **kwargs)
                    self.assertEqual(pairs(a), [(1.0, 5.0)])

    def test_unknown_kwarg_is_type_error(self):
        with self.assertRaises(TypeError):
            Animated(Real).add_waypoint(0, 1, bogus=1)

    def test_frames_need_fps(self):
        with self.assertRaises(ValueError):
            Animated(Real).add_waypoint("12f", 1)
        a = Animated(Real).add_waypoint("12f", 1, fps=24)
        self.assertEqual(a.waypoints[0].time, 0.5)

    def test_ref_waypoint_serializes_as_use_without_child(self):
        target = Real(2, id="r")
        el = xml(Animated(Real).add_waypoint(0, Ref(target)))[0]
        self.assertEqual(el.get("use"), "r")
        self.assertEqual(len(el), 0)

    def test_ref_of_other_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            Animated(Vector).add_waypoint(0, Ref(Real(1, id="r")))

    def test_plain_use_string_ref_is_accepted(self):
        el = xml(Animated(Real).add_waypoint(0, Ref("other.sif#x")))[0]
        self.assertEqual(el.get("use"), "other.sif#x")

    def test_animated_attributes_serialize(self):
        el = xml(Animated(Real, id="a", guid="g", interpolation="linear"))
        self.assertEqual(
            el.attrib,
            {"type": "real", "id": "a", "guid": "g", "interpolation": "linear"},
        )

    def test_waypoint_attribute_names(self):
        a = Animated(Real).add_waypoint(
            1, 1, before="clamped", after="auto", tension=0.5,
            temporal_tension=0.25, continuity=0.1, bias=-0.2,
        )
        el = xml(a)[0]
        self.assertEqual(el.get("temporal-tension"), "0.25")
        self.assertEqual(el.get("tension"), "0.5")
        self.assertEqual(el.get("bias"), "-0.2")
        self.assertEqual((el.get("before"), el.get("after")), ("clamped", "auto"))

    def test_invalid_interpolation_is_rejected(self):
        with self.assertRaises(ValueError):
            Animated(Real, interpolation="bouncy")
        with self.assertRaises(ValueError):
            Animated(Real).add_waypoint(0, 1, before="bouncy")

    def test_valueless_waypoint_error_names_time(self):
        w = Waypoint()
        w.time = 2
        with self.assertRaisesRegex(ValueError, "no value.*time=2"):
            xml(w)

    def test_waypoint_without_time_is_rejected(self):
        w = Waypoint()
        w.value = Real(1)
        with self.assertRaisesRegex(ValueError, "no time"):
            xml(w)

    def test_untyped_kind_arguments_are_rejected(self):
        with self.assertRaises(TypeError):
            Animated("real")  # type: ignore[arg-type]

    def test_non_addable_kind_rejects_add(self):
        from synpyg.value import String

        a = Animated(String).add_waypoint(0, "a")
        with self.assertRaises(TypeError):
            a.add_waypoint(1, "b", add=True)


if __name__ == "__main__":
    unittest.main()
