import unittest
from xml.etree import ElementTree as ET

from synpyg.animated import Animated
from synpyg.base import Param, Property
from synpyg.fields import Kind
from synpyg.layer import CircleLayer, Layer
from synpyg.value import Const, Real, Value, ValueKind, Vector


class ValueKindTest(unittest.TestCase):
    def test_is_a_kind(self):
        self.assertIsInstance(ValueKind.of(Real), Kind)

    def test_of_is_shared_per_type_and_passes_kinds_through(self):
        k = ValueKind.of(Real)
        self.assertIs(ValueKind.of(Real), k)
        self.assertIs(ValueKind.of(k), k)
        self.assertIs(Real.as_kind(), k)

    def test_equality_is_by_wrapped_type(self):
        self.assertEqual(ValueKind(Real), ValueKind.of(Real))
        self.assertEqual(hash(ValueKind(Real)), hash(ValueKind.of(Real)))
        self.assertNotEqual(ValueKind(Real), ValueKind(Vector))

    def test_rejects_non_value_types(self):
        for bad in (int, "Real", Real(1.0), None, [Real]):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    ValueKind.of(bad)  # type: ignore[arg-type]
                with self.assertRaises(TypeError):
                    ValueKind(bad)  # type: ignore[arg-type]

    def test_coerce_wraps_raw_input_and_keeps_instances(self):
        k = ValueKind.of(Vector)
        v = k.coerce([1, 2])
        self.assertIsInstance(v, Vector)
        self.assertEqual(v.data, (1.0, 2.0))
        self.assertIs(k.coerce(v), v)
        with self.assertRaises(ValueError):
            k.coerce("nope")

    def test_coerce_does_not_accept_animated(self):
        with self.assertRaises(ValueError):
            ValueKind.of(Real).coerce(Real.new_animated())

    def test_tag_name_and_repr(self):
        k = ValueKind.of(Real)
        self.assertEqual((k.tag, k.name, repr(k)), ("real", "Real", "ValueKind(Real)"))

    def test_dump_is_not_text(self):
        with self.assertRaises(TypeError):
            ValueKind.of(Real).dump(Real(1.0))


class TakesAKindTest(unittest.TestCase):
    def test_param_accepts_type_or_kind(self):
        class L(Layer):
            a = Param(Real)
            b = Param(ValueKind(Real))

        self.assertEqual(L.a.kind, L.b.kind)
        self.assertIs(L.b.typed, Real)
        x = L("x")
        x.a, x.b = 1, 2
        self.assertEqual((x.a.value.data, x.b.value.data), (1.0, 2.0))
        self.assertEqual(x.b.kind, Real.as_kind())

    def test_param_rejects_a_non_kind(self):
        with self.assertRaises(TypeError):
            Param(int)  # type: ignore[arg-type]

    def test_property_accepts_type_or_kind_and_defaults_to_string(self):
        self.assertEqual(Property(Real).kind, ValueKind.of(Real))
        self.assertEqual(Property(ValueKind(Real)).kind, ValueKind.of(Real))
        self.assertEqual(Property().kind.name, "String")

    def test_animated_accepts_type_or_kind(self):
        self.assertEqual(Animated(Real).kind, Animated(ValueKind(Real)).kind)
        a = Animated(ValueKind.of(Vector)).add_waypoint(0, [1, 2])
        self.assertEqual(a.to_xml_element(ET).get("type"), "vector")

    def test_tagless_kinds_cannot_be_animated(self):
        for cls in (Value, Const):
            with self.subTest(cls.__name__):
                with self.assertRaises(TypeError):
                    Animated(ValueKind.of(cls))

    def test_animated_from_a_separately_built_kind_is_accepted(self):
        c = CircleLayer()
        anim = Animated(ValueKind(Real))  # not the shared instance
        c.radius = anim
        self.assertIs(c.radius.value, anim)

    def test_mismatched_animated_error_names_both_types(self):
        c = CircleLayer()
        with self.assertRaisesRegex(ValueError, "Vector.*Real"):
            c.radius = Animated(Vector)

    def test_as_prop_carries_the_kind(self):
        p = Real(2.0).as_prop("r")
        self.assertEqual(p.kind, Real.as_kind())
        self.assertEqual(p.name, "r")


if __name__ == "__main__":
    unittest.main()
