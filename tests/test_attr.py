import unittest

from etc.field import (
    Attr,
    BoolAttr,
    FloatAttr,
    IntAttr,
    StringAttr,
    TimeAttr,
    iter_attrs,
    timep,
)


class Example:
    when = TimeAttr()
    label = StringAttr()
    ratio = FloatAttr()
    count = IntAttr()
    enabled = BoolAttr()


class TestTimep(unittest.TestCase):
    def test_colon_formats(self):
        self.assertEqual(timep("1:30"), 90.0)
        self.assertEqual(timep("1:02:03"), 3723.0)

    def test_units_and_numbers(self):
        self.assertEqual(timep("250ms"), 0.25)
        self.assertEqual(timep("2.5s"), 2.5)
        self.assertEqual(timep("3.25"), 3.25)
        self.assertEqual(timep(4), 4.0)
        self.assertEqual(timep(1.5), 1.5)

    def test_invalid_type(self):
        with self.assertRaises(ValueError):
            timep(object())


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
        self.assertEqual(Example.when.dumps(obj), "3723.0s")

    def test_dumps_serializes_numeric_assignment(self):
        obj = Example()
        obj.when = 0.25
        self.assertEqual(Example.when.dumps(obj), "0.25s")

    def test_base_dumps_is_not_implemented(self):
        with self.assertRaisesRegex(NotImplementedError, "Attr"):
            Attr().dumps(Example())


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


if __name__ == "__main__":
    unittest.main()
