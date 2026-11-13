import unittest

from synpyg.field import (
    Field,
    BoolAttr,
    FloatAttr,
    IntAttr,
    QuadFloatAttr,
    StringAttr,
    StringEnumAttr,
    TimeAttr,
    iter_attrs,
    iter_fields,
)
from synpyg.timeutil import tosec


class Example:
    when = TimeAttr()
    label = StringAttr()
    ratio = FloatAttr()
    count = IntAttr()
    enabled = BoolAttr()


class TestTimeParser(unittest.TestCase):
    def test_colon_formats(self):
        self.assertEqual(tosec("1:30"), 90.0)
        self.assertEqual(tosec("1:02:03"), 3723.0)

    def test_units_and_numbers(self):
        self.assertEqual(tosec("250ms"), 0.25)
        self.assertEqual(tosec("2.5s"), 2.5)
        self.assertEqual(tosec("3.25"), 3.25)
        self.assertEqual(tosec(4), 4.0)
        self.assertEqual(tosec(1.5), 1.5)

    def test_frames_require_fps(self):
        with self.assertRaises(ValueError):
            tosec("5f")

    def test_frames_with_fps(self):
        self.assertEqual(tosec("5f", fps=25), 0.2)
        self.assertEqual(tosec("30f", fps=60), 0.5)

    def test_frames_fractional(self):
        self.assertEqual(tosec("1.5f", fps=30), 0.05)

    def test_fps_ignored_for_non_frames(self):
        self.assertEqual(tosec("1s", fps=25), 1.0)  # fps unused, no error

    def test_invalid_type(self):
        with self.assertRaises(ValueError):
            tosec(object())  # type: ignore

    def test_zero_frames_need_no_fps(self):
        self.assertEqual(tosec("0f"), 0.0)
        self.assertEqual(tosec("-0f"), 0.0)

    def test_nonzero_frames_still_need_fps(self):
        with self.assertRaises(ValueError):
            tosec("1f")


class TestTimeAttr(unittest.TestCase):
    def test_class_access_returns_descriptor(self):
        self.assertIsInstance(Example.when, TimeAttr)

    def test_set_normalizes_value_to_seconds(self):
        obj = Example()
        obj.when = "1:02:03"
        self.assertEqual(obj.when, 3723.0)
        self.assertIsInstance(obj.when, float)

    def test_accepts_numeric_values(self):
        obj = Example()
        obj.when = 1
        self.assertEqual(obj.when, 1.0)
        obj.when = 1.25
        self.assertEqual(obj.when, 1.25)

    def test_missing_value_raises_attribute_error(self):
        with self.assertRaises(AttributeError):
            _ = Example().when

    def test_delete_value(self):
        obj = Example()
        obj.when = "2s"
        del obj.when
        with self.assertRaises(AttributeError):
            _ = obj.when

    def test_instances_store_values_independently(self):
        first = Example()
        second = Example()
        first.when = "1s"
        second.when = "2s"
        self.assertEqual(first.when, 1.0)
        self.assertEqual(second.when, 2.0)

    def test_string_dumps(self):
        obj = Example()
        obj.label = "hello"
        self.assertEqual(Example.label.dumps(obj), "hello")

    def test_float_dumps(self):
        obj = Example()
        obj.ratio = 0.875
        self.assertEqual(Example.ratio.dumps(obj), "0.875")

    def test_int_dumps(self):
        obj = Example()
        obj.count = 42
        self.assertEqual(Example.count.dumps(obj), "42")

    def test_bool_dumps(self):
        obj = Example()
        obj.enabled = True
        self.assertEqual(Example.enabled.dumps(obj), "true")
        obj.enabled = False
        self.assertEqual(Example.enabled.dumps(obj), "false")

    def test_dumps_serializes_seconds_with_unit_suffix(self):
        obj = Example()
        obj.when = "1:02:03"
        self.assertEqual(Example.when.dumps(obj), "3723s")

    def test_dumps_serializes_numeric_assignment(self):
        obj = Example()
        obj.when = 0.25
        self.assertEqual(Example.when.dumps(obj), "0.25s")

    def test_base_dumps_is_not_implemented(self):
        with self.assertRaisesRegex(NotImplementedError, "Field"):
            Field().dumps(Example())


class BaseAttrs:
    base_label = StringAttr()
    base_count = IntAttr()


class MiddleAttrs(BaseAttrs):
    middle_enabled = BoolAttr()


class ChildAttrs(MiddleAttrs):
    child_when = TimeAttr()
    child_ratio = FloatAttr()


class TestIterAttrs(unittest.TestCase):
    def test_iterates_attrs_defined_across_multiple_inheritance_levels(self):
        obj = ChildAttrs()
        obj.base_label = "inherited"
        # obj.base_count = 7
        obj.middle_enabled = True
        obj.child_when = "1:30"
        obj.child_ratio = 0.5

        attrs = list(iter_attrs(obj))

        self.assertEqual(
            [(name, type(descriptor), value) for name, descriptor, value in attrs],
            [
                ("child_when", TimeAttr, 90.0),
                ("child_ratio", FloatAttr, 0.5),
                ("middle_enabled", BoolAttr, True),
                ("base_label", StringAttr, "inherited"),
            ],
        )

    def test_subclass_descriptor_overrides_base_descriptor(self):
        class Parent:
            value = StringAttr()

        class Child(Parent):
            value = IntAttr()

        obj = Child()
        obj.value = 12

        attrs = list(iter_attrs(obj))

        self.assertEqual(len(attrs), 1)
        self.assertEqual(attrs[0][0], "value")
        self.assertIsInstance(attrs[0][1], IntAttr)
        self.assertEqual(attrs[0][2], 12)

    def test_iter_fields_has_no_duplicates_for_overrides(self):
        class Parent:
            value = StringAttr()

        class Child(Parent):
            value = IntAttr()

        fields = list(iter_fields(Child()))
        self.assertEqual([(n, type(d)) for n, d in fields], [("value", IntAttr)])

    def test_non_field_override_shadows_base_field(self):
        class Parent:
            value = StringAttr()

        class Child(Parent):
            value = None

        self.assertEqual(list(iter_fields(Child())), [])


class TestCoerce(unittest.TestCase):
    def test_float_attr_coerces_string(self):
        obj = Example()
        obj.ratio = "0.875"  # type: ignore
        self.assertEqual(obj.ratio, 0.875)
        self.assertIsInstance(obj.ratio, float)

    def test_int_attr_coerces_string(self):
        obj = Example()
        obj.count = "42"  # type: ignore
        self.assertEqual(obj.count, 42)

    def test_bool_attr_parses_strings(self):
        obj = Example()
        obj.enabled = "false"  # type: ignore
        self.assertIs(obj.enabled, False)
        obj.enabled = "true"  # type: ignore
        self.assertIs(obj.enabled, True)

    def test_bool_attr_rejects_garbage_as_false(self):
        obj = Example()
        obj.enabled = "nonsense"  # type: ignore
        self.assertIs(obj.enabled, False)  # or raise, depending on your parser


class TestStringEnumAttr(unittest.TestCase):
    def test_accepts_allowed_value(self):
        class O:
            status = StringEnumAttr(choices=("on", "off"))

        o = O()
        o.status = "on"
        self.assertEqual(o.status, "on")

    def test_rejects_disallowed_value(self):
        class O:
            status = StringEnumAttr(choices=("on", "off"))

        with self.assertRaises(ValueError):
            O().status = "maybe"

    def test_class_access_returns_descriptor(self):
        class O:
            status = StringEnumAttr(choices=("on", "off"))

        self.assertIsInstance(O.status, StringEnumAttr)

    def test_explicit_name(self):
        class O:
            status = StringEnumAttr(choices=("on", "off"), name="state")

        self.assertEqual(O.status.ctx.get("name"), "state")

    # def test_choices_are_copied(self):
    #     allowed = ["on", "off"]
    #     a = StringEnumAttr(choices=allowed)
    #     allowed.append("maybe")
    #     self.assertEqual(a.ctx.get("choices"), ("on", "off"))

    def test_dumps(self):
        class O:
            status = StringEnumAttr(choices=("on", "off"))

        o = O()
        o.status = "off"
        self.assertEqual(O.status.dumps(o), "off")


class TestQuadFloatAttr(unittest.TestCase):
    class O:
        quad = QuadFloatAttr()

    def test_coerces_ints_to_floats(self):
        o = self.O()
        o.quad = (1, 2, 3, 4)
        self.assertEqual(o.quad, (1.0, 2.0, 3.0, 4.0))
        self.assertIsInstance(o.quad[0], float)

    def test_accepts_list_and_generator(self):
        o = self.O()
        o.quad = [1.0, 2.0, 3.0, 4.0]
        self.assertEqual(o.quad, (1.0, 2.0, 3.0, 4.0))
        o.quad = (float(i) for i in range(4))
        self.assertEqual(o.quad, (0.0, 1.0, 2.0, 3.0))

    def test_rejects_wrong_length(self):
        o = self.O()
        with self.assertRaises(ValueError):
            o.quad = (1.0, 2.0, 3.0)
        with self.assertRaises(ValueError):
            o.quad = (1.0, 2.0, 3.0, 4.0, 5.0)

    def test_rejects_non_numeric(self):
        o = self.O()
        with self.assertRaises((TypeError, ValueError)):
            o.quad = (1.0, 2.0, "x", 4.0)

    def test_stored_as_tuple(self):
        o = self.O()
        o.quad = [1, 2, 3, 4]
        self.assertIsInstance(o.quad, tuple)

    def test_class_access_returns_descriptor(self):
        self.assertIsInstance(self.O.quad, QuadFloatAttr)

    def test_dumps(self):
        o = self.O()
        o.quad = (1, 2.5, 3, 4)
        self.assertEqual(self.O.quad.dumps(o), "1 2.5 3 4")

    def test_missing_raises_attribute_error(self):
        with self.assertRaises(AttributeError):
            _ = self.O().quad


if __name__ == "__main__":
    unittest.main()
