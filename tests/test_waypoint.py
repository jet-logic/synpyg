import unittest

from synpyg.animated import Animated, Waypoint
from synpyg.value import Real, Vector


def vec_anim() -> Animated:
    return Vector.new_animated()


def times(anim: Animated) -> list[str]:
    return [w.get("time") for w in anim.to_xml_element()]


class TimeFormattingTest(unittest.TestCase):
    def test_formats(self):
        cases = [
            (0, "0s"),
            (1.5, "1.5s"),
            (2, "2s"),
            ("1s", "1s"),  # was "1ss"
            ("500ms", "0.5s"),
            ("1:30", "90s"),
            ("12f", "12f"),  # was "12fs"
            (complex(1, 12), "1s 12f"),  # was "(1+12j)s"
        ]
        for raw, want in cases:
            with self.subTest(raw=raw):
                w = Waypoint()
                w.time = raw
                w.value = Real(1.0)
                self.assertEqual(w.to_xml_element().get("time"), want)

    def test_bad_time_fails_at_add_not_at_save(self):
        for bad in ("soon", "1.5f", None):
            with self.subTest(bad=bad):
                with self.assertRaises((ValueError, TypeError)):
                    vec_anim().add_waypoint(bad, [0, 0])


class ValueCoercionTest(unittest.TestCase):
    def test_raw_list_becomes_vector(self):
        a = vec_anim().add_waypoint(0, [1, 2])
        self.assertIsInstance(a.waypoints[0].value, Vector)
        x = a.to_xml_element()[0].find("vector/x")
        self.assertEqual(x.text, "1")

    def test_existing_instance_is_kept(self):
        v = Vector([3, 4])
        a = vec_anim().add_waypoint(0, v)
        self.assertIs(a.waypoints[0].value, v)

    def test_wrong_type_is_rejected(self):
        with self.assertRaises(ValueError):
            vec_anim().add_waypoint(0, Real(1.0))

    def test_invalid_raw_value_is_rejected(self):
        with self.assertRaises(ValueError):
            vec_anim().add_waypoint(0, "nope")

    def test_other_value_types(self):
        a = Animated()
        a._type = Real
        a.add_waypoint(0, 2).add_waypoint(1, Real(3.5))
        self.assertEqual([w.value.data for w in a.waypoints], [2.0, 3.5])


class ValuelessWaypointTest(unittest.TestCase):
    def test_serializing_without_value_raises(self):
        w = Waypoint().set_params(before="clamped")
        w.time = 1
        with self.assertRaisesRegex(ValueError, "no value.*time=1"):
            w.to_xml_element()

    def test_without_value_or_time(self):
        with self.assertRaisesRegex(ValueError, "no value"):
            Waypoint().to_xml_element()


class OrderingTest(unittest.TestCase):
    def test_sorted_by_time_on_output(self):
        a = vec_anim().add_waypoint(4, [6, 0]).add_waypoint(1, [0, 0]).add_waypoint(2, [3, 0])
        self.assertEqual(times(a), ["1s", "2s", "4s"])

    def test_mixed_time_spellings_sort_by_seconds(self):
        a = vec_anim().add_waypoint("2s", [0, 0]).add_waypoint(1, [0, 0]).add_waypoint("1500ms", [0, 0])
        self.assertEqual(times(a), ["1s", "1.5s", "2s"])

    def test_equal_times_keep_insertion_order(self):
        a = vec_anim().add_waypoint(1, [0, 0]).add_waypoint(0, [5, 5]).add_waypoint(1, [9, 9])
        xs = [w.find("vector/x").text for w in a.to_xml_element()]
        self.assertEqual(xs, ["5", "0", "9"])

    def test_sorting_does_not_mutate_waypoints(self):
        a = vec_anim().add_waypoint(4, [0, 0]).add_waypoint(1, [0, 0])
        a.to_xml_element()
        self.assertEqual([w.time for w in a.waypoints], [4, 1])

    def test_frames_keep_insertion_order(self):
        # frames can't be compared with seconds without the canvas fps
        a = vec_anim().add_waypoint("2s", [0, 0]).add_waypoint("12f", [0, 0]).add_waypoint(1, [0, 0])
        self.assertEqual(times(a), ["2s", "12f", "1s"])


if __name__ == "__main__":
    unittest.main()
