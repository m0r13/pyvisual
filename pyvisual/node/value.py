import math
import numpy as np
import imgui
from collections import OrderedDict
from pyvisual.node.base import Node, prepare_port_spec
from pyvisual.node import dtype
from pyvisual.editor import widget
from collections import defaultdict

class InputBool(Node):
    class Meta:
        outputs = [
            {"name" : "output", "dtype" : dtype.bool, "manual_input" : True}
        ]
        options = {
            "category" : "input",
            "show_title" : False
        }

class OutputBool(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.bool, "manual_input" : False}
        ]
        options = {
            "category" : "output",
            "show_title" : False
        }

class InputEvent(Node):
    class Meta:
        outputs = [
            {"name" : "output", "dtype" : dtype.event, "manual_input" : True}
        ]
        options = {
            "category" : "input",
            "show_title" : False
        }

class OutputEvent(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.event, "manual_input" : False}
        ]
        options = {
            "category" : "output",
            "show_title" : False
        }

class InputFloat(Node):
    class Meta:
        outputs = [
            {"name" : "output", "dtype" : dtype.float, "manual_input" : True}
        ]
        options = {
            "category" : "input",
            "show_title" : False
        }

class OutputFloat(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.float, "manual_input" : False}
        ]
        options = {
            "category" : "output",
            "show_title" : False
        }

class SetFloatVar(Node):

    instances = defaultdict(lambda: set())

    class Meta:
        inputs = [
            {"name" : "name", "dtype" : dtype.str, "hide" : True},
            {"name" : "input", "dtype" : dtype.float}
        ]
        options = {
            "category" : "output",
            "show_title" : False
        }

    def __init__(self):
        super().__init__()

    def start(self, graph):
        SetFloatVar.instances[graph].add(self)

    def _show_custom_ui(self):
        imgui.push_item_width(widget.WIDGET_WIDTH)
        changed, v = imgui.input_text("", self.get("name"), 255, imgui.INPUT_TEXT_ENTER_RETURNS_TRUE)
        if changed:
            self.get_input("name").value = v

class GetFloatVar(Node):
    class Meta:
        inputs = [
            {"name" : "name", "dtype" : dtype.str, "hide" : True}
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float, "manual_input" : True}
        ]
        options = {
            "category" : "input",
            "show_title" : False
        }

    def __init__(self):
        super().__init__(always_evaluate=True)

        self.graph = None
        self.connected_node = None

    def get_sub_nodes(self, include_self):
        sub_nodes = super().get_sub_nodes(include_self)
        if self.connected_node is not None:
            return sub_nodes + [self.connected_node]
        return sub_nodes

    def start(self, graph):
        self.graph = graph

    def _evaluate(self):
        assert self.graph is not None

        if self.get_input("name").has_changed:
            name = self.get("name")

            self.connected_node = None
            for node in SetFloatVar.instances[self.graph]:
                if node.get("name") == name:
                    self.connected_node = node
                    break

        if self.connected_node is not None:
            self.set("output", self.connected_node.get("input"))

    def _show_custom_ui(self):
        imgui.push_item_width(widget.WIDGET_WIDTH)
        if self.connected_node is None:
            imgui.push_style_color(imgui.COLOR_TEXT, 1.0, 0.0, 0.0)
        changed, v = imgui.input_text("", self.get("name"), 255, imgui.INPUT_TEXT_ENTER_RETURNS_TRUE)
        if self.connected_node is None:
            imgui.pop_style_color()
        if changed:
            self.get_input("name").value = v

class InputColor(Node):
    class Meta:
        outputs = [
            {"name" : "output", "dtype" : dtype.color, "manual_input" : True},
        ]
        options = {
            "category" : "input",
            "show_title" : False
        }

class OutputColor(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.color, "manual_input" : False},
        ]
        options = {
            "category" : "output",
            "show_title" : False
        }

class Float2Color(Node):
    class Meta:
        inputs = [
            {"name" : "r", "dtype" : dtype.float, "dtype_args" : {"range" : (0.0, 1.0)}},
            {"name" : "g", "dtype" : dtype.float, "dtype_args" : {"range" : (0.0, 1.0)}},
            {"name" : "b", "dtype" : dtype.float, "dtype_args" : {"range" : (0.0, 1.0)}},
            {"name" : "a", "dtype" : dtype.float, "dtype_args" : {"range" : (0.0, 1.0), "default" : 1.0}},
        ]
        outputs = [
            {"name" : "color", "dtype" : dtype.color},
        ]
        options = {
            "category" : "conversion",
            "show_title" : True
        }

    def _evaluate(self):
        self.set("color", np.array([
            self.get("r"),
            self.get("g"),
            self.get("b"),
            self.get("a")
        ], dtype=np.float32))

class Color2Float(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.color},
        ]
        outputs = [
            {"name" : "r", "dtype" : dtype.float, "dtype_args" : {"range" : (0.0, 1.0)}},
            {"name" : "g", "dtype" : dtype.float, "dtype_args" : {"range" : (0.0, 1.0)}},
            {"name" : "b", "dtype" : dtype.float, "dtype_args" : {"range" : (0.0, 1.0)}},
            {"name" : "a", "dtype" : dtype.float, "dtype_args" : {"range" : (0.0, 1.0), "default" : 1.0}},
        ]
        options = {
            "category" : "conversion",
            "show_title" : True
        }

    def _evaluate(self):
        color = self.get("input")
        self.set("r", color[0])
        self.set("g", color[1])
        self.set("b", color[2])
        self.set("a", color[3])

class Scale(Node):
    class Meta:
        inputs = [
            {"name" : "x", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "y", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.mat4},
        ]

    def _evaluate(self):
        transform = np.array([[self.get("x"), 0.0, 0.0, 0.0],
                              [0.0, self.get("y"), 0.0, 0.0],
                              [0.0, 0.0, 1.0, 0.0],
                              [0.0, 0.0, 0.0, 1.0]], dtype=np.float32).T
        self.set("output", transform)

class Rotate(Node):
    class Meta:
        inputs = [
            {"name" : "theta", "dtype" : dtype.float},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.mat4},
        ]

    def _evaluate(self):
        theta = math.radians(self.get("theta"))
        sinT = math.sin(theta)
        cosT = math.cos(theta)
        transform = np.array([[cosT, -sinT, 0.0, 0.0],
                              [sinT, cosT, 0.0, 0.0],
                              [0.0, 0.0, 1.0, 0.0],
                              [0.0, 0.0, 0.0, 1.0]], dtype=np.float32).T
        self.set("output", transform)

class Translate(Node):
    class Meta:
        inputs = [
            {"name" : "x", "dtype" : dtype.float},
            {"name" : "y", "dtype" : dtype.float},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.mat4},
        ]

    def _evaluate(self):
        transform = np.array([[1.0, 0.0, 0.0, self.get("x")],
                              [0.0, 1.0, 0.0, self.get("y")],
                              [0.0, 0.0, 1.0, 0.0],
                              [0.0, 0.0, 0.0, 1.0]], dtype=np.float32).T
        self.set("output", transform)

class Dot(Node):
    class Meta:
        inputs = [
            {"name" : "t1", "dtype" : dtype.mat4},
            {"name" : "t2", "dtype" : dtype.mat4},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.mat4},
        ]

    def _evaluate(self):
        self.set("output", np.dot(self.get("t1"), self.get("t2")))

class Test(Node):
    class Meta:
        inputs = [
            {"name" : "number", "dtype" : dtype.int, "dtype_args" : {"range" : [0, float("inf")]}},
            {"name" : "checkbox", "dtype" : dtype.bool},
        ]
        outputs = [
        ]

    def _update_custom_ports(self):
        self.custom_input_ports = OrderedDict()
        if self.get("checkbox"):
            port_spec = {"name" : "test", "dtype" : dtype.str}
            prepare_port_spec(port_spec, True)
            self.custom_input_ports["i_name"] = port_spec

        self.custom_output_ports = OrderedDict()
        for i in range(int(self.get("number"))):
            name = "output%d" % i
            port_spec = {"name" : name, "dtype" : dtype.float, "manual_input" : True}
            prepare_port_spec(port_spec, False)
            self.custom_output_ports["o_%s" % name] = port_spec
        self.update_ports()

    def _evaluate(self):
        if self.have_inputs_changed("number", "checkbox"):
            self._update_custom_ports()
