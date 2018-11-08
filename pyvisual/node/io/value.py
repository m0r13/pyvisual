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

class Float2Vec2(Node):
    class Meta:
        inputs = [
            {"name" : "x", "dtype" : dtype.float, "dtype_args" : {}},
            {"name" : "y", "dtype" : dtype.float, "dtype_args" : {}},
        ]
        outputs = [
            {"name" : "vec2", "dtype" : dtype.vec2},
        ]
        options = {
            "category" : "conversion",
            "show_title" : True
        }

    def _evaluate(self):
        self.set("vec2", np.array([
            self.get("x"),
            self.get("y")
        ], dtype=np.float32))

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

class Vec22Float(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.vec2},
        ]
        outputs = [
            {"name" : "x", "dtype" : dtype.float},
            {"name" : "y", "dtype" : dtype.float},
        ]
        options = {
            "category" : "conversion",
            "show_title" : True
        }

    def _evaluate(self):
        vec = self.get("input")
        self.set("x", vec[0])
        self.set("y", vec[1])

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


# TODO where to put vars to?

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

        self.graph = None
        self.stopped = True
        # TODO when graph is deserialized that contains duplicate nodes
        # the order of who is duplicate vs. who is original might change
        self.duplicate = False

    @property
    def valid(self):
        return not self.duplicate and bool(self.name)

    @property
    def name(self):
        return self.get("name")
    @name.setter
    def name(self, name):
        self.get_input("name").value = name

    def start(self, graph):
        self.graph = graph
        self.stopped = False
        SetFloatVar.instances[graph].add(self)

    def _show_custom_ui(self):
        imgui.push_item_width(widget.WIDGET_WIDTH)
        if self.duplicate:
            imgui.push_style_color(imgui.COLOR_TEXT, 1.0, 0.0, 0.0)
        changed, v = imgui.input_text("", self.get("name"), 255, imgui.INPUT_TEXT_ENTER_RETURNS_TRUE)
        if self.duplicate:
            imgui.pop_style_color()
            if imgui.is_item_hovered():
                imgui.set_tooltip("Name is a duplicate!")
        if changed:
            self.name = v

    def _evaluate(self):
        if self.have_inputs_changed("name"):
            name = self.name
            for node in SetFloatVar.instances[self.graph]:
                if node != self and node.valid and node.name == name:
                    self.duplicate = True
                    return
            self.duplicate = False

    def stop(self):
        assert self.graph is not None

        self.stopped = True
        SetFloatVar.instances[self.graph].remove(self)

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
        # TODO maybe a needs_evaluate method that we can overwrite here?!
        super().__init__(always_evaluate=True)

        self.graph = None
        self.connected_node = None

    @property
    def name(self):
        return self.get("name")
    @name.setter
    def name(self, name):
        self.get_input("name").value = name

    def get_sub_nodes(self, include_self):
        sub_nodes = super().get_sub_nodes(include_self)
        if self.connected_node is not None:
            return sub_nodes + [self.connected_node]
        return sub_nodes

    def start(self, graph):
        self.graph = graph

    def evaluate(self, *args, **kwargs):
        if self.connected_node is not None:
            if self.connected_node.stopped:
                self.name = ""

        super().evaluate(*args, **kwargs)

    def _evaluate(self):
        assert self.graph is not None

        if self.have_inputs_changed("name"):
            name = self.name

            self.connected_node = None
            if not name:
                return
            for node in SetFloatVar.instances[self.graph]:
                if node.valid and node.name == name:
                    self.connected_node = node
                    break

        if self.connected_node is not None:
            self.set("output", self.connected_node.get("input"))

    def _show_custom_ui(self):
        preview = "<none>"
        if self.connected_node is not None:
            preview = self.connected_node.name
        if imgui.begin_combo("", preview):
            nodes = SetFloatVar.instances[self.graph]

            is_selected = self.connected_node is None
            opened, selected = imgui.selectable("<none>", is_selected)
            if opened:
                self.name = ""
            if is_selected:
                imgui.set_item_default_focus()
            imgui.separator()

            for node in sorted(nodes, key=lambda node: node.name):
                if not node.valid:
                    continue
                is_selected = node == self.connected_node
                opened, selected = imgui.selectable(node.name, is_selected)
                if opened:
                    self.name = node.name
                if is_selected:
                    imgui.set_item_default_focus()
            imgui.end_combo()
