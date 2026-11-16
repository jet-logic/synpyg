import unittest
from xml.etree import ElementTree as ET

from synpyg.animated import Animated, Waypoint
from synpyg.base import Property
from synpyg.layer import CircleLayer
from synpyg.ref import Ref
from synpyg.value import Integer, Real, Vector


def xml(node) -> str:
    return ET.tostring(node.to_xml_element(ET), encoding="unicode")


class RefTest(unittest.TestCase):
    def test_string_target(self):
        r = Ref("glow")
        self.assertEqual(r.use, "glow")
        self.assertIsNone(r.kind)

    def test_bad_targets(self):
        with self.assertRaises(ValueError):
            Ref("")
        with self.assertRaises(TypeError):
            Ref(3.5)  # type: ignore
        with self.assertRaises(TypeError):
            Ref(Ref("a"))  # type: ignore

    def test_object_target_reads_id_late(self):
        node = Real(1.0)
        r = Ref(node)
        with self.assertRaisesRegex(ValueError, "no id"):
            r.use
        node.id = "glow"
        self.assertEqual(r.use, "glow")

    def test_kind_of_targets(self):
        self.assertEqual(Ref(Real(1.0)).kind, Real.as_kind())
        self.assertEqual(Ref(Vector.new_animated()).kind, Vector.as_kind())

    def test_animated_target_uses_its_id(self):
        a = Real.new_animated()
        a.id = "pulse"
        self.assertEqual(Ref(a).use, "pulse")


class PropertyRefTest(unittest.TestCase):
    def test_set_value_accepts_matching_ref(self):
        p = Property(Real, "amount")
        r = Ref(Real(1.0, id="glow"))
        p.set_value(r)
        self.assertIs(p.value, r)
        self.assertTrue(p.has_value)

    def test_kind_mismatch(self):
        p = Property(Real, "amount")
        with self.assertRaisesRegex(ValueError, "does not match"):
            p.set_value(Ref(Integer(1, id="n")))
        with self.assertRaises(ValueError):
            p.set_value(Ref(Vector.new_animated()))
        self.assertIsNone(p.value)

    def test_plain_string_ref_matches_any_kind(self):
        for kind in (Real, Integer, Vector):
            p = Property(kind, "x")
            p.set_value(Ref("elsewhere.sif#thing"))
            self.assertEqual(p.to_xml_element(ET).get("use"), "elsewhere.sif#thing")

    def test_xml_is_attribute_only(self):
        p = Property(Real, "amount", Ref(Real(1.0, id="glow")))
        self.assertEqual(xml(p), '<param name="amount" use="glow" />')

    def test_xml_error_when_target_has_no_id(self):
        p = Property(Real, "amount", Ref(Real(1.0)))
        with self.assertRaisesRegex(ValueError, "no id"):
            p.to_xml_element(ET)

    def test_param_descriptor_assignment(self):
        layer = CircleLayer()
        layer.radius = Ref(Real(2.0, id="r"))
        el = layer.to_xml_element(ET)
        param = next(e for e in el if e.get("name") == "radius")
        self.assertEqual(param.get("use"), "r")
        self.assertEqual(len(param), 0)

    def test_param_descriptor_rejects_wrong_kind(self):
        layer = CircleLayer()
        with self.assertRaises(ValueError):
            layer.radius = Ref(Vector((0, 0), id="v"))

    def test_replacing_ref_with_value_drops_use(self):
        p = Property(Real, "amount", Ref("glow"))
        p.set_value(0.5)
        el = p.to_xml_element(ET)
        self.assertIsNone(el.get("use"))
        self.assertEqual(el[0].get("value"), "0.5")

    def test_as_animated_keeps_the_link_as_first_waypoint(self):
        p = Property(Real, "amount", Ref(Real(1.0, id="glow")))
        anim = p.as_animated()
        self.assertIs(p.value, anim)
        (wp,) = anim.waypoints
        self.assertIsInstance(wp.value, Ref)
        self.assertEqual(wp.to_xml_element(ET).get("use"), "glow")


class WaypointRefTest(unittest.TestCase):
    def test_add_waypoint_with_ref(self):
        a = Real.new_animated()
        a.add_waypoint(0, 0.0).add_waypoint(1, Ref(Real(5.0, id="peak")))
        first, second = a.to_xml_element(ET)
        self.assertEqual(len(first), 1)
        self.assertEqual(second.get("use"), "peak")
        self.assertEqual(len(second), 0)

    def test_waypoint_options_survive_beside_use(self):
        a = Real.new_animated()
        a.add_waypoint(1, Ref("peak"), before="linear", after="ease")
        el = a.to_xml_element(ET)[0]
        self.assertEqual(
            (el.get("time"), el.get("before"), el.get("after"), el.get("use")),
            ("1s", "linear", "ease", "peak"),
        )

    def test_kind_mismatch(self):
        a = Real.new_animated()
        with self.assertRaises(ValueError):
            a.add_waypoint(0, Ref(Vector((0, 0), id="v")))
        self.assertEqual(a.waypoints, [])

    def test_waypoints_with_refs_still_sort_by_time(self):
        a = Real.new_animated()
        a.add_waypoint(2, Ref("b")).add_waypoint(1, Ref("a"))
        self.assertEqual([w.get("use") for w in a.to_xml_element(ET)], ["a", "b"])

    def test_bare_waypoint(self):
        w = Waypoint()
        w.time = 1
        w.value = Ref("x")
        self.assertEqual(w.to_xml_element(ET).get("use"), "x")


if __name__ == "__main__":
    unittest.main()
