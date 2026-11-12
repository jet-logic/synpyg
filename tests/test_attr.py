import unittest

from etc.field import FloatAttr, TimeAttr, timep


class Example:
    when = TimeAttr()


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


if __name__ == "__main__":
    unittest.main()


# target design
w = Example()
# w.radius = 0.87            # OK (editor see float type)
# w.radius = "loose"         # ❌ type error: str is not float
