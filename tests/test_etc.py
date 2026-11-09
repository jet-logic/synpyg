import json
import unittest

from synpyg.base import Field, params
from synpyg.base import Property
from synpyg.value import Integer


class Test(unittest.TestCase):
    def test_value(self):
        from synpyg.layer import SolidColorLayer

        s = SolidColorLayer()
        print(repr(s.amount))
        print(repr(s.blend_method))

    def test_dynamic_property(self):
        from synpyg.layer import SolidColorLayer

        s = SolidColorLayer()
        self.assertIsInstance(s.amount, Property)
        self.assertEqual(s.amount.value.value, 1.0)
        self.assertIsInstance(s.blend_method, Property)
        self.assertIsInstance(s.blend_method.value, Integer)
        self.assertIs(s.blend_method.value.value, 1)
        self.assertSequenceEqual(
            [k for k, v in s._enum_params()], ["amount", "blend_method"]
        )
        s.flag = Property(Integer(67))  # type: ignore
        self.assertSequenceEqual(
            [k for k, v in s._enum_params()], ["amount", "blend_method", "flag"]
        )


if __name__ == "__main__":
    unittest.main()
