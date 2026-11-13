import unittest
from xml.etree import ElementTree as ET

from synpyg.canvas import Canvas
from synpyg.value import Real, Time


class FramesTest(unittest.TestCase):
    def test_canvas_resolves_frames_with_its_fps(self):
        c = Canvas(fps=24, begin_time="12f", end_time="48f")
        self.assertEqual(c.begin_time, 0.5)
        self.assertEqual(c.end_time, 2.0)
        a = c.to_xml_element(ET).attrib
        self.assertEqual((a["begin-time"], a["end-time"]), ("0.5s", "2s"))

    def test_canvas_frames_use_fps_current_at_assignment(self):
        c = Canvas(fps=24)
        c.begin_time = "24f"
        self.assertEqual(c.begin_time, 1.0)
        c.fps = 12
        c.end_time = "24f"
        self.assertEqual(c.end_time, 2.0)
        self.assertEqual(c.begin_time, 1.0)  # not re-derived

    def test_canvas_nonzero_frames_without_valid_fps_still_fail(self):
        with self.assertRaises(ValueError):
            Canvas(fps=0, begin_time="1f")

    def test_time_value_with_fps(self):
        self.assertEqual(Time("12f", fps=24).data, 0.5)
        with self.assertRaises(ValueError):
            Time("12f")
        self.assertEqual(Time(1.5).data, 1.5)

    def test_waypoint_with_fps(self):
        a = Real.new_animated()
        a.add_waypoint("24f", 1, fps=24).add_waypoint(2, 2)
        self.assertEqual([w.time for w in a.waypoints], [1.0, 2.0])
        with self.assertRaises(ValueError):
            a.add_waypoint("1f", 3)
        self.assertEqual(len(a.waypoints), 2)  # failed add leaves nothing behind

    def test_waypoint_kwargs_still_work_with_fps(self):
        a = Real.new_animated()
        a.add_waypoint("6f", 1, fps=12, before="clamped")
        self.assertEqual(a.waypoints[0].before, "clamped")
        self.assertEqual(a.waypoints[0].time, 0.5)


if __name__ == "__main__":
    unittest.main()
