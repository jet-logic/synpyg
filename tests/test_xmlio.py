import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from synpyg import (
    Canvas,
    MissingLayerTypeError,
    SIFParseError,
    UnsupportedLayerError,
    parse_sif,
)
from synpyg.layer import CircleLayer, GroupLayer
from synpyg.ref import Ref
from synpyg.valuenode import Add
from synpyg.value import (
    Angle,
    Boolean,
    Color,
    DashItemList,
    DynamicList,
    Gradient,
    Integer,
    List,
    Matrix,
    Real,
    Segment,
    Spline,
    String,
    Time,
    Transformation,
    Vector,
    WidthPointList,
)
from synpyg.xmlio import _parse_value


class CanvasXMLParseTests(unittest.TestCase):
    def test_parse_round_trip_layers_and_nested_canvas(self):
        canvas = Canvas(width=640, height=360, fps=30, view_box=(-4, 2.25, 4, -2.25))
        circle = canvas.add_circle_layer("Circle")
        circle.radius = 2.5
        circle.origin = (1, 2)
        circle.color = (0.1, 0.2, 0.3, 1)
        circle.invert = True
        group = canvas.add_group_layer("Group")
        nested = group.add_solid_color_layer("Nested")
        nested.color = (1, 0, 0, 1)

        parsed = Canvas.from_xml_element(canvas.to_xml_element(ET))
        self.assertEqual((parsed.width, parsed.height, parsed.fps), (640, 360, 30.0))
        self.assertEqual([layer.layer_type for layer in parsed], ["circle", "group"])
        parsed_circle = parsed.first_child()
        self.assertIsInstance(parsed_circle, CircleLayer)
        self.assertEqual(parsed_circle.radius.value.data, 2.5)
        self.assertEqual(parsed_circle.origin.value.data, (1.0, 2.0))
        self.assertEqual(parsed_circle.color.value.data, (0.1, 0.2, 0.3, 1.0))
        self.assertTrue(parsed_circle.invert.value.data)
        parsed_group = list(parsed)[1]
        self.assertIsInstance(parsed_group, GroupLayer)
        self.assertEqual([layer.layer_type for layer in parsed_group], ["solid_color"])

        before = ET.tostring(canvas.to_xml_element(ET), encoding="unicode")
        after = ET.tostring(parsed.to_xml_element(ET), encoding="unicode")
        self.assertEqual(after, before)

    def test_parse_external_canvas_reference(self):
        source = '''<canvas version="1.2" width="480" height="270" fps="24">
          <layer type="group" version="0.1" active="true">
            <param name="canvas"><canvas use="other.sif#canvas" /></param>
          </layer>
        </canvas>'''
        canvas = parse_sif(source)
        group = canvas.first_child()
        self.assertEqual(group.canvas.value.use, "other.sif#canvas")
        output = group.to_xml_element(ET).find("param[@name='canvas']/canvas")
        self.assertEqual(output.get("use"), "other.sif#canvas")

    def test_parse_file_path(self):
        canvas = Canvas()
        canvas.add_circle_layer().radius = 5
        with tempfile.TemporaryDirectory() as tmp:
            filename = Path(tmp) / "test.sif"
            canvas.save_xml(filename)
            parsed = Canvas.from_xml(filename)
        self.assertEqual(parsed.first_child().radius.value.data, 5.0)

    def test_unknown_layer_type_is_a_clear_error(self):
        source = '''<canvas version="1.2" width="480" height="270" fps="24">
          <layer type="some_future_layer" version="1" active="true" />
        </canvas>'''
        with self.assertRaisesRegex(UnsupportedLayerError, "some_future_layer"):
            parse_sif(source)

    def test_missing_layer_type_is_a_clear_error(self):
        source = '''<canvas version="1.2" width="480" height="270" fps="24">
          <layer version="1" active="true" />
        </canvas>'''
        with self.assertRaises(MissingLayerTypeError):
            parse_sif(source)

    def test_unknown_attributes_and_params_are_preserved(self):
        source = '''<canvas version="1.2" width="480" height="270" fps="24" future-root="yes">
          <layer type="circle" version="0.1" active="true" future-layer="kept">
            <param name="radius"><real value="3" /></param>
            <param name="future_parameter" custom="yes"><future_value a="b">payload</future_value></param>
          </layer>
          <meta name="author">example</meta>
        </canvas>'''
        parsed = parse_sif(source)
        output = parsed.to_xml_element(ET)
        self.assertEqual(output.get("future-root"), "yes")
        layer = output.find("layer")
        self.assertEqual(layer.get("future-layer"), "kept")
        raw_param = layer.find("param[@name='future_parameter']")
        self.assertEqual(raw_param.get("custom"), "yes")
        self.assertEqual(raw_param.find("future_value").text, "payload")
        self.assertEqual(output.find("meta").text, "example")

    def test_bad_xml_is_wrapped_in_sif_parse_error(self):
        with self.assertRaises(SIFParseError):
            parse_sif("<canvas>")

    def test_empty_known_parameter_is_preserved(self):
        source = '''<canvas version="1.2">
          <layer type="circle" version="0.1" active="true">
            <param name="radius" guid="radius-guid" />
          </layer>
        </canvas>'''
        parsed = parse_sif(source)
        param = parsed.to_xml_element(ET).find("layer/param[@name='radius']")
        self.assertEqual(param.get("guid"), "radius-guid")

    def test_unknown_param_on_known_layer_does_not_fail(self):
        source = '''<canvas version="1.2" width="480" height="270" fps="24">
          <layer type="circle" version="0.1" active="true">
            <param name="radius"><real value="1" /></param>
            <param name="new_synfig_param"><real value="2" /></param>
          </layer>
        </canvas>'''
        parsed = parse_sif(source)
        self.assertEqual(parsed.first_child().radius.value.data, 1.0)
        params = parsed.to_xml_element(ET).findall("layer/param")
        self.assertEqual([p.get("name") for p in params], ["radius", "new_synfig_param"])

    def test_group_canvas_can_reference_canvas_with_param_use(self):
        source = '''<canvas version="1.2" width="480" height="270" fps="24">
          <layer type="group" version="0.1" active="true">
            <param name="canvas" use="library_canvas" />
          </layer>
        </canvas>'''
        parsed = parse_sif(source)
        group = parsed.first_child()
        self.assertIsInstance(group.canvas.value, Ref)
        self.assertEqual(list(group), [])
        self.assertIn('use="library_canvas"', ET.tostring(group.to_xml_element(ET), encoding="unicode"))

    def test_linkable_value_node_can_be_a_typed_parameter_value(self):
        source = '''<canvas version="1.2" width="480" height="270" fps="24">
          <layer type="circle" version="0.1" active="true">
            <param name="origin">
              <add><lhs><vector><x>1</x><y>2</y></vector></lhs>
                   <rhs><vector><x>3</x><y>4</y></vector></rhs></add>
            </param>
          </layer>
        </canvas>'''
        parsed = parse_sif(source)
        value = parsed.first_child().origin.value
        self.assertIsInstance(value, Add)
        xml = parsed.to_xml_element(ET)
        self.assertEqual(xml.find("layer/param[@name='origin']/add/lhs/vector/x").text, "1")

    def test_linkable_value_node_references_can_be_encoded_as_attributes(self):
        source = '''<canvas version="1.2" width="480" height="270" fps="24">
          <defs>
            <vector id="position"><x>1</x><y>2</y></vector>
            <add id="sum" lhs="position"><rhs><vector><x>3</x><y>4</y></vector></rhs></add>
          </defs>
        </canvas>'''
        parsed = parse_sif(source)
        self.assertIn("sum", parsed.defs)
        self.assertIsInstance(parsed.defs["sum"], Add)
        self.assertIsInstance(parsed.defs["sum"].links["lhs"], Ref)

    def test_nested_canvas_attributes_are_retained_when_present(self):
        source = '''<canvas version="1.2" width="480" height="270" fps="24">
          <layer type="group" version="0.1" active="true">
            <param name="canvas"><canvas width="100" height="50" fps="12" xres="900">
              <layer type="circle" version="0.1" active="true" />
            </canvas></param>
          </layer>
        </canvas>'''
        parsed = parse_sif(source)
        nested = parsed.first_child().canvas.value
        self.assertEqual((nested.width, nested.height, nested.fps), (100, 50, 12.0))
        nested_xml = parsed.to_xml_element(ET).find("layer/param/canvas")
        self.assertEqual(nested_xml.get("width"), "100")
        self.assertEqual(nested_xml.get("xres"), "900")

    def test_canvas_attributes_and_document_metadata_follow_sif_defaults(self):
        source = '''<canvas version="0.9" width="200" height="450" xres="2834.6" yres="2834.6"
            view-box="-1 2.25 1 -2.25" antialias="1" fps="12" begin-time="0f"
            end-time="2s" bgcolor="0.5 0.5 0.5 1">
          <name>Simple Walk</name>
          <keyframe time="0f" active="true">Step 1</keyframe>
        </canvas>'''
        parsed = parse_sif(source)
        self.assertEqual(parsed.end_time, 2.0)
        out = parsed.to_xml_element(ET)
        self.assertEqual(out.get("bgcolor"), "0.5 0.5 0.5 1")
        self.assertEqual(out.find("name").text, "Simple Walk")
        self.assertEqual(out.find("keyframe").get("time"), "0f")

    def test_missing_optional_root_attributes_use_canvas_defaults(self):
        parsed = parse_sif('<canvas version="1.2" />')
        self.assertEqual((parsed.width, parsed.height, parsed.fps), (480, 270, 24.0))

    def test_sif_string_character_data_and_meta_content_attribute(self):
        source = '''<canvas version="1.2">
          <meta name="author" content="Example Artist" />
          <layer type="circle" version="0.1" active="true">
            <param name="radius"><real value="1" /></param>
          </layer>
        </canvas>'''
        parsed = parse_sif(source)
        self.assertEqual(parsed.meta["author"], "Example Artist")


class ValueXMLParseTests(unittest.TestCase):
    def parse_again(self, value):
        element = value.to_xml_element(ET)
        return _parse_value(element, fps=24.0, where=value.tag)

    def test_scalar_and_composite_values(self):
        values = [
            Real(1.25),
            Integer(3),
            Boolean(True),
            String("hello"),
            Angle(90),
            Time(1.5),
            Color((0.1, 0.2, 0.3, 0.4)),
            Vector((2, 3)),
            Gradient([(0, (0, 0, 0, 1)), (1, (1, 1, 1, 1))]),
            Segment((0, 0), (1, 0), (2, 0), (1, 0)),
            Spline([((0, 0), (1, 0)), ((2, 0), (0, 1))], loop=True),
            WidthPointList([(0, 1), (1, 0.5)], loop=True),
            DashItemList([(0.1, 0.2), (0.4, 0.1)]),
            Transformation((1, 2), 30, 10, (2, 3)),
            Matrix((1, 0, 0, 0, 1, 0, 0, 0, 1)),
            List([Real(1), String("x")]),
            DynamicList([Real(1), Real(2)], type="real"),
        ]
        for value in values:
            with self.subTest(value=type(value).__name__):
                parsed = self.parse_again(value)
                self.assertIs(type(parsed), type(value))

    def test_string_character_data_is_supported(self):
        parsed = _parse_value(ET.fromstring("<string>Hello Synfig</string>"), fps=24, where="string")
        self.assertEqual(parsed.data, "Hello Synfig")
        self.assertEqual(ET.tostring(parsed.to_xml_element(ET), encoding="unicode"), "<string>Hello Synfig</string>")

    def test_animation_and_waypoint_references(self):
        source = '''<animated type="real" id="anim" interpolation="linear">
          <waypoint time="0s"><real value="1" /></waypoint>
          <waypoint time="12f" after="linear" use="other" />
        </animated>'''
        from synpyg.xmlio import _parse_animated

        parsed = _parse_animated(ET.fromstring(source), fps=24, where="defs/animated")
        self.assertEqual(parsed.id, "anim")
        self.assertEqual(parsed.waypoints[0].time, 0.0)
        self.assertEqual(parsed.waypoints[1].time, 0.5)
        self.assertIsInstance(parsed.waypoints[1].value, Ref)
        self.assertEqual(parsed.waypoints[1].value.use, "other")

    def test_defs_are_imported_as_exported_nodes(self):
        source = '''<canvas version="1.2" width="480" height="270" fps="24">
          <defs><real id="radius" value="4" /></defs>
          <layer type="circle" version="0.1" active="true">
            <param name="radius" use="radius" />
          </layer>
        </canvas>'''
        parsed = parse_sif(source)
        self.assertIn("radius", parsed.defs)
        self.assertEqual(parsed.defs["radius"].data, 4.0)
        self.assertEqual(parsed.first_child().radius.value.use, "radius")

    def test_registered_custom_layer_class(self):
        from synpyg.layer import Layer
        from synpyg.xmlio import register_layer

        class CustomLayer(Layer):
            def __init__(self, **kwargs):
                super().__init__("custom_layer", version="1", **kwargs)

        register_layer("custom_layer", CustomLayer)
        parsed = parse_sif('''<canvas version="1.2" width="480" height="270" fps="24">
          <layer type="custom_layer" version="2" active="true" />
        </canvas>''')
        self.assertIsInstance(parsed.first_child(), CustomLayer)
        self.assertEqual(parsed.first_child().version, "2")

    def test_parameter_and_value_static_metadata_is_preserved(self):
        source = '''<canvas version="1.2" width="480" height="270" fps="24">
          <layer type="circle" version="0.1" active="true">
            <param name="radius" custom-param="retained"><real value="2" static="true" /></param>
          </layer>
        </canvas>'''
        parsed = parse_sif(source)
        xml = parsed.to_xml_element(ET)
        param = xml.find("layer/param")
        self.assertEqual(param.get("custom-param"), "retained")
        self.assertEqual(param.find("real").get("static"), "true")

    def test_animated_waypoint_can_hold_a_linkable_value_node(self):
        source = '''<animated type="vector">
          <waypoint time="0s"><add>
            <lhs><vector><x>1</x><y>2</y></vector></lhs>
            <rhs><vector><x>3</x><y>4</y></vector></rhs>
          </add></waypoint>
        </animated>'''
        from synpyg.xmlio import _parse_animated
        parsed = _parse_animated(ET.fromstring(source), fps=24, where="animated")
        self.assertIsInstance(parsed.waypoints[0].value, Add)
        self.assertIn("<add>", ET.tostring(parsed.to_xml_element(ET), encoding="unicode"))


if __name__ == "__main__":
    unittest.main()
