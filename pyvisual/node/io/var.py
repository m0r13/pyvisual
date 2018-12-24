import math
import numpy as np
import imgui
from collections import OrderedDict
from pyvisual.node.base import Node, prepare_port_spec
from pyvisual.node import dtype
from pyvisual.editor import widget
from collections import defaultdict

class SetVar(Node):

    # subclasses must have their own defaultdict(lambda: set()) instance here
    instances = None

    class Meta:
        options = {
            "virtual" : True
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

    @property
    def collapsed_title(self):
        return "var: %s" % self.name

    def start(self, graph):
        self.graph = graph
        self.stopped = False
        self.instances[graph.parent].add(self)

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
            for node in self.instances[self.graph.parent]:
                if node != self and node.valid and node.name == name:
                    self.duplicate = True
                    return
            self.duplicate = False

    def stop(self):
        assert self.graph is not None

        self.stopped = True
        # seemed to happen once. dunno why, not so bad
        try:
            self.instances[self.graph.parent].remove(self)
        except KeyError:
            pass

class GetVar(Node):
    
    # subclasses must have their respective SetXXXVar class here
    SetVar = None

    class Meta:
        options = {
            "virtual" : True
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

    @classmethod
    def get_presets(cls, graph):
        presets = []
        for node in cls.SetVar.instances.get(graph.parent, []):
            presets.append((node.name, {"i_name" : node.name}))
        return presets

    @property
    def collapsed_title(self):
        return "var: %s" % self.name

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
            for node in self.SetVar.instances[self.graph.parent]:
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
            nodes = self.SetVar.instances[self.graph.parent]

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

class SetFloatVar(SetVar):
    class Meta:
        inputs = [
            {"name" : "name", "dtype" : dtype.str, "hide" : True},
            {"name" : "input", "dtype" : dtype.float}
        ]
        options = {
            "show_title" : False
        }

    instances = defaultdict(lambda: set())

class GetFloatVar(GetVar):
    class Meta:
        inputs = [
            {"name" : "name", "dtype" : dtype.str, "hide" : True}
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float, "manual_input" : True}
        ]
        options = {
            "show_title" : False
        }

    SetVar = SetFloatVar

class SetTextureVar(SetVar):
    class Meta:
        inputs = [
            {"name" : "name", "dtype" : dtype.str, "hide" : True},
            {"name" : "input", "dtype" : dtype.tex2d}
        ]
        options = {
            "show_title" : False
        }

    instances = defaultdict(lambda: set())

class GetTextureVar(GetVar):
    class Meta:
        inputs = [
            {"name" : "name", "dtype" : dtype.str, "hide" : True}
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.tex2d}
        ]
        options = {
            "show_title" : False
        }

    SetVar = SetTextureVar

