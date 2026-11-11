from dataclasses import dataclass, field, fields
from typing import Any
import unittest

from synpyg.animated import Waypoint
from synpyg.layer import GroupLayer


def attr(*args, **kwargs):
    return field(*args, **kwargs)


@dataclass
class Base:
    x: Any = 15.0
    y: int = field(default=0, metadata={"TAG": "METADATA"})


@dataclass(init=False)
class C(Base):
    z: int = 10
    x: int = 15
    w: str = attr(metadata={"TAG": "METADATA"})


class Test(unittest.TestCase):
    # def test_value(self):
    #     c = C()
    #     for f in fields(c):
    #         print(f)
    #     # print(c.w)

    def test_Waypoint(self):
        w = Waypoint()
        # w.before
        w.time = 4
        w.after = "qerreq"
        w.temporal_tension = 0.87
        for f in fields(w):
            print(f.name, f.metadata)
        self.assertSequenceEqual(
            sorted(w.__dict__.keys()), ["after", "temporal_tension", "time"]
        )

        print(w._etree.tostring(w.to_xml_element()))

    # def test_GroupLayer(self):
    #     g = GroupLayer()
    #     g.extra.set_value([5, 4])
    #     print(g._etree.tostring(g.to_xml_element()))


if __name__ == "__main__":
    unittest.main()
