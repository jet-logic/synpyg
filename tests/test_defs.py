import os
import tempfile
import unittest
from xml.etree import ElementTree as ET

from synpyg.canvas import Canvas
from synpyg.ref import Ref
from synpyg.value import Integer, Real, Vector


def tree(canvas: Canvas) -> ET.Element:
    return canvas.to_xml_element(ET)


class ExportTest(unittest.TestCase):
    def test_export_sets_id_registers_and_returns_node(self):
        c = Canvas()
        node = Real(1.0)
        self.assertIs(c.export("glow", node), node)
        self.assertEqual(node.id, "glow")
        self.assertIs(c.defs["glow"], node)

    def test_export_animated(self):
        c = Canvas()
        a = c.export("pulse", Real.new_animated().add_keyframe(0, 1.0))
        self.assertEqual(a.id, "pulse")
        self.assertIs(c.defs["pulse"], a)

    def test_defs_keeps_export_order_and_is_read_only(self):
        c = Canvas()
        c.export("b", Real(1.0))
        c.export("a", Real(2.0))
        self.assertEqual(list(c.defs), ["b", "a"])
        with self.assertRaises(TypeError):
            c.defs["x"] = Real(3.0)  # type: ignore

    def test_same_node_same_id_is_a_no_op(self):
        c = Canvas()
        node = c.export("glow", Real(1.0))
        self.assertIs(c.export("glow", node), node)
        self.assertEqual(len(c.defs), 1)

    def test_node_created_with_the_same_id_can_be_exported(self):
        c = Canvas()
        c.export("glow", Real(1.0, id="glow"))
        self.assertIn("glow", c.defs)

    def test_conflicts(self):
        c = Canvas()
        node = c.export("glow", Real(1.0))
        with self.assertRaisesRegex(ValueError, "already exported as"):
            c.export("other", node)
        with self.assertRaisesRegex(ValueError, "already exported"):
            c.export("glow", Real(2.0))
        with self.assertRaisesRegex(ValueError, "already has id"):
            c.export("x", Real(2.0, id="y"))
        self.assertEqual(list(c.defs), ["glow"])

    def test_failed_export_leaves_node_untouched(self):
        c = Canvas()
        c.export("glow", Real(1.0))
        node = Real(2.0)
        with self.assertRaises(ValueError):
            c.export("glow", node)
        self.assertNotIn("id", node.__dict__)

    def test_bad_ids(self):
        c = Canvas()
        for bad in ("", "a:b", "a#b", None, 3):
            with self.subTest(bad=bad):
                with self.assertRaises((ValueError, TypeError)):
                    c.export(bad, Real(1.0))  # type: ignore
        self.assertEqual(len(c.defs), 0)

    def test_bad_nodes(self):
        c = Canvas()
        for bad in (1.0, "x", Ref("x")):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    c.export("n", bad)  # type: ignore

    def test_each_canvas_has_its_own_registry(self):
        a, b = Canvas(), Canvas()
        a.export("glow", Real(1.0))
        self.assertEqual(len(b.defs), 0)


class DefsXmlTest(unittest.TestCase):
    def test_no_defs_element_when_nothing_is_exported(self):
        c = Canvas()
        c.add_circle_layer()
        self.assertIsNone(tree(c).find("defs"))

    def test_defs_comes_first_and_carries_ids(self):
        c = Canvas()
        c.add_circle_layer()
        c.export("glow", Real(1.5))
        c.export("pulse", Vector.new_animated().add_keyframe(0, (0, 0)))
        root = tree(c)
        self.assertEqual([e.tag for e in root], ["defs", "layer"])
        real, anim = root.find("defs")  # type: ignore
        self.assertEqual(
            (real.tag, real.get("id"), real.get("value")), ("real", "glow", "1.5")
        )
        self.assertEqual(
            (anim.tag, anim.get("id"), anim.get("type")),
            ("animated", "pulse", "vector"),
        )

    def test_ref_in_a_param_points_at_the_export(self):
        c = Canvas()
        layer = c.add_circle_layer()
        glow = c.export("glow", Real(0.5))
        layer.amount = Ref(glow)
        root = tree(c)
        param = next(p for p in root.find("layer") if p.get("name") == "amount")  # type: ignore
        self.assertEqual((param.get("use"), len(param)), ("glow", 0))
        self.assertEqual(root.find("defs/real").get("id"), "glow")  # type: ignore

    def test_ref_in_a_waypoint(self):
        c = Canvas()
        layer = c.add_circle_layer()
        peak = c.export("peak", Real(5.0))
        layer.amount.as_animated().add_keyframe(1, Ref(peak))
        root = tree(c)
        wp = root.find("layer/param/animated/waypoint")
        self.assertEqual(wp.get("use"), "peak")  # type: ignore

    def test_ref_inside_a_group_resolves_against_the_root_canvas(self):
        c = Canvas()
        group = c.add_group_layer()
        inner = group.add_circle_layer()
        inner.radius = Ref(c.export("r", Real(2.0)))
        root = tree(c)
        self.assertEqual(root.find("defs/real").get("id"), "r")  # type: ignore
        used = [p.get("use") for p in root.iter("param") if p.get("use")]
        self.assertEqual(used, ["r"])

    def test_output_is_stable(self):
        c = Canvas()
        c.add_circle_layer().amount = Ref(c.export("glow", Real(1.0)))
        self.assertEqual(ET.tostring(tree(c)), ET.tostring(tree(c)))

    def test_save_xml_writes_defs(self):
        c = Canvas()
        c.export("glow", Real(1.0))
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "out.sif")
            c.save_xml(path)
            self.assertEqual(
                ET.parse(path).getroot().find("defs/real").get("id"), "glow"
            )  # type: ignore

    def test_exported_animated_may_reference_another_export(self):
        c = Canvas()
        peak = c.export("peak", Real(5.0))
        c.export("pulse", Real.new_animated().add_keyframe(0, Ref(peak)))
        wp = tree(c).find("defs/animated/waypoint")
        self.assertEqual(wp.get("use"), "peak")  # type: ignore


class CheckDefsTest(unittest.TestCase):
    def test_ref_to_a_node_that_was_never_exported(self):
        c = Canvas()
        c.add_circle_layer().amount = Ref(Real(1.0, id="glow"))
        with self.assertRaisesRegex(ValueError, "not exported from this canvas"):
            tree(c)

    def test_ref_to_a_node_exported_from_another_canvas(self):
        a, b = Canvas(), Canvas()
        glow = a.export("glow", Real(1.0))
        b.add_circle_layer().amount = Ref(glow)
        with self.assertRaisesRegex(ValueError, "not exported from this canvas"):
            tree(b)

    def test_dangling_ref_inside_a_group_and_a_waypoint(self):
        c = Canvas()
        inner = c.add_group_layer().add_circle_layer()
        inner.amount.as_animated().add_keyframe(0, Ref(Real(1.0, id="x")))
        with self.assertRaisesRegex(ValueError, "waypoint"):
            tree(c)

    def test_dangling_ref_inside_an_export(self):
        c = Canvas()
        c.export("pulse", Real.new_animated().add_keyframe(0, Ref(Real(1.0, id="x"))))
        with self.assertRaisesRegex(ValueError, "export 'pulse'"):
            tree(c)

    def test_plain_string_refs_are_not_checked(self):
        c = Canvas()
        c.add_circle_layer().amount = Ref("elsewhere.sif#glow")
        self.assertEqual(
            [p.get("use") for p in tree(c).iter("param") if p.get("use")],
            ["elsewhere.sif#glow"],
        )

    def test_node_with_an_id_cannot_be_embedded(self):
        c = Canvas()
        glow = c.export("glow", Real(1.0))
        c.add_circle_layer().amount = glow  # forgot Ref(...)
        with self.assertRaisesRegex(ValueError, "embedded"):
            tree(c)

    def test_waypoint_value_with_an_id_cannot_be_embedded(self):
        c = Canvas()
        layer = c.add_circle_layer()
        layer.amount.as_animated().add_keyframe(0, Real(1.0, id="x"))
        with self.assertRaisesRegex(ValueError, "embedded"):
            tree(c)

    def test_renaming_an_exported_node_is_caught(self):
        c = Canvas()
        node = c.export("glow", Real(1.0))
        node.id = "other"
        with self.assertRaisesRegex(ValueError, "now has id"):
            tree(c)

    def test_plain_values_without_ids_are_unaffected(self):
        c = Canvas()
        c.add_circle_layer().radius = 2.0
        c.add_circle_layer().amount.as_animated().add_keyframe(0, 1.0)
        tree(c)  # no error


class IdOnValuesTest(unittest.TestCase):
    def test_value_writes_its_id(self):
        self.assertEqual(Integer(3, id="n").to_xml_element(ET).get("id"), "n")
        self.assertEqual(Vector((1, 2), id="v").to_xml_element(ET).get("id"), "v")

    def test_value_without_id_writes_none(self):
        self.assertIsNone(Real(1.0).to_xml_element(ET).get("id"))


if __name__ == "__main__":
    unittest.main()
