import unittest
from xml.etree import ElementTree as ET

from synpyg.animated import Animated, Waypoint
from synpyg.base import Param
from synpyg.layer import CircleLayer, GroupLayer, Layer, MotionBlurLayer
from synpyg.value import Real, Vector


def param_names(layer):
    return [p.get("name") for p in layer.to_xml_element(ET).findall("param")]


class ParamDescriptorTest(unittest.TestCase):
    def test_class_access_returns_descriptor(self):
        self.assertIsInstance(CircleLayer.radius, Param)
        self.assertEqual(CircleLayer.radius.name, "radius")

    def test_declared_params_inherit_base_first(self):
        self.assertEqual(
            list(CircleLayer._params),
            [
                "z_depth",
                "amount",
                "blend_method",
                "color",
                "radius",
                "feather",
                "origin",
                "invert",
                "falloff",
            ],
        )

    def test_instances_do_not_share_properties(self):
        a, b = CircleLayer(), CircleLayer()
        self.assertIsNot(a.radius, b.radius)
        a.radius = 2
        self.assertFalse(b.radius.has_value)

    def test_read_is_stable_and_harmless(self):
        c = CircleLayer("x")
        self.assertIs(c.radius, c.radius)
        # previously: AttributeError at serialization time after a plain read
        self.assertEqual(param_names(c), [])

    def test_assignment_validates_and_sets(self):
        c = CircleLayer()
        c.radius = 1.5
        self.assertIsInstance(c.radius.value, Real)
        self.assertEqual(c.radius.value.data, 1.5)  # type: ignore
        c.origin = [1, 2]
        self.assertIsInstance(c.origin.value, Vector)
        with self.assertRaises(ValueError):
            c.origin = "nope"

    def test_assign_value_instance_passthrough(self):
        c = CircleLayer()
        v = Real(3.0)
        c.radius = v
        self.assertIs(c.radius.value, v)

    def test_delete_unsets(self):
        c = CircleLayer()
        c.radius = 1
        del c.radius
        self.assertEqual(param_names(c), [])

    def test_output_order_is_declaration_order_not_access_order(self):
        a, b = MotionBlurLayer(), MotionBlurLayer()
        a.subsample_end = 1
        a.aperture = 0.5
        b.aperture = 0.5
        b.subsample_end = 1
        self.assertEqual(param_names(a), param_names(b))
        self.assertEqual(param_names(a), ["aperture", "subsample_end"])

    def test_adhoc_property_still_serialized_last(self):
        c = CircleLayer()
        c.radius = 1
        c.flag = Real(1.0).as_prop("flag")  # type: ignore
        self.assertEqual(param_names(c), ["radius", "flag"])

    def test_trailing_underscore_is_dropped_from_name(self):
        class L(Layer):
            from_ = Param(Real)
            z = Param(Real, "z-depth")

        self.assertEqual(L.from_.name, "from")
        self.assertEqual(L.z.name, "z-depth")

    def test_set_params_unknown_raises_typeerror(self):
        with self.assertRaises(TypeError):
            CircleLayer()._assign(radiuss=1)

    def test_set_params_keeps_existing_animation(self):
        c = CircleLayer()
        anim = c.origin.as_animated()
        anim.add_waypoint(0, Vector([0, 0]))
        c._assign(radius=1)  # touches a different param; origin untouched
        self.assertIs(c.origin.value, anim)

    def test_as_animated_twice_returns_same_object(self):
        # previously: NameError (Animated only imported under TYPE_CHECKING)
        c = CircleLayer()
        c.origin = [0, 0]
        a = c.origin.as_animated()
        self.assertIsInstance(a, Animated)
        self.assertIs(c.origin.as_animated(), a)

    def test_group_layer_params(self):
        g = GroupLayer("g")
        g.origin = [1, 1]
        self.assertEqual(param_names(g), ["origin", "canvas"])


class AttrDescriptorTest(unittest.TestCase):
    def test_unset_attr_raises_and_is_not_stored(self):
        w = Waypoint()
        with self.assertRaises(AttributeError):
            w.before
        self.assertEqual(w.__dict__, {})

    def test_xml_names_and_formatting(self):
        w = Waypoint()
        w.time = 2
        w.temporal_tension = 0.5
        w.value = Real(1.0)
        el = w.to_xml_element(ET)
        self.assertEqual(el.attrib, {"time": "2s", "temporal-tension": "0.5"})

    def test_set_params_unknown_raises_typeerror(self):
        with self.assertRaises(TypeError):
            Waypoint()._assign(nope=1)


class NewAnimatedTest(unittest.TestCase):
    def test_every_concrete_const_type_can_animate(self):
        from synpyg.value import (
            Angle,
            Boolean,
            Color,
            Integer,
            Real,
            String,
            Time,
            Vector,
        )

        for cls, sample in [
            (Real, 1.5),
            (Integer, 3),
            (Boolean, True),
            (String, "hi"),
            (Angle, 45.0),
            (Time, 1.0),
            (Color, [1, 0, 0, 1]),
            (Vector, [1, 2]),
        ]:
            with self.subTest(cls.__name__):
                a = cls.new_animated()
                self.assertIsInstance(a, Animated)
                self.assertIs(a._type, cls)
                a.add_waypoint(0, sample)
                el = a.to_xml_element(ET)
                self.assertEqual(el.get("type"), cls.tag)

    def test_as_animated_on_non_vector_param(self):
        c = CircleLayer()
        c.radius = 1.0
        a = c.radius.as_animated()
        self.assertIsInstance(a, Animated)
        self.assertIs(a._type, Real)
        # second call returns the same Animated, not a new one
        self.assertIs(c.radius.as_animated(), a)

    def test_abstract_bases_still_reject(self):
        from synpyg.value import Value, Const, Vec

        for cls in (Value, Const, Vec):
            with self.subTest(cls.__name__):
                with self.assertRaises(NotImplementedError):
                    cls.new_animated()


class PropertyAnimatedTest(unittest.TestCase):
    def test_as_animated_preserves_value_by_default(self):
        c = CircleLayer()
        c.origin = [3, 4]

        anim = c.origin.as_animated()

        self.assertEqual(len(anim.waypoints), 1)
        self.assertEqual(anim.waypoints[0].time, 0)
        self.assertEqual(anim.waypoints[0].value.data, (3.0, 4.0))

    def test_as_animated_without_preserving_value(self):
        c = CircleLayer()
        c.origin = [3, 4]

        anim = c.origin.as_animated(preserve=False)

        self.assertEqual(len(anim.waypoints), 0)

    def test_as_animated_without_existing_value(self):
        c = CircleLayer()

        anim = c.origin.as_animated()

        self.assertEqual(len(anim.waypoints), 0)

    def test_as_animated_twice_returns_same_animation(self):
        c = CircleLayer()
        c.origin = [3, 4]

        first = c.origin.as_animated()
        second = c.origin.as_animated(preserve=False)

        self.assertIs(first, second)
        self.assertEqual(len(second.waypoints), 1)


if __name__ == "__main__":
    unittest.main()
