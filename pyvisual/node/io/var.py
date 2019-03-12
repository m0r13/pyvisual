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

        # TODO
        self.value = 0.0
        self.value_has_changed = False

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
    def descriptive_title(self):
        return "set var: %s" % self.name

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

        value = self.get_input("input")
        if value.has_changed or self._last_evaluated == 0.0:
            self.value = value.value
            self.value_has_changed = True
            # evaluate once more to trigger reset
            self.force_evaluate()
        else:
            self.value_has_changed = False

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
    FORCE_UPDATE = False

    class Meta:
        options = {
            "virtual" : True
        }
    
    def __init__(self):
        # TODO maybe a needs_evaluate method that we can overwrite here?!
        super().__init__(always_evaluate=True)

        self.graph = None
        self.connected_node = None
        self._force_value_update = False

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
    def descriptive_title(self):
        return "get var: %s" % self.name

    def start(self, graph):
        self.graph = graph

    def update_input_nodes(self):
        # overwrite this to have connected node added as input node
        super().update_input_nodes()

        if self.connected_node is not None:
            self.input_nodes.add(self.connected_node)
        # TODO this is quite a hack
        self.graph.parent.reset_sorted_instances()

    def evaluate(self, *args, **kwargs):
        if self.connected_node is not None:
            if self.connected_node.stopped:
                self.name = ""

        super().evaluate(*args, **kwargs)

    def _evaluate(self):
        assert self.graph is not None

        input_name = self.get_input("name")
        input_name_changed = input_name.has_changed
        if input_name_changed:
            name = input_name.value

            self.connected_node = None
            if not name:
                return
            for node in self.SetVar.instances[self.graph.parent]:
                if node.valid and node.name == name:
                    self.connected_node = node
                    # okay slight problem
                    # SetXXXVar is associated in first evaluation
                    # only in second evaluation the nodes are executed in correct order then
                    # and by then the value might be changed on the SetXXXVar but we've missed it
                    # just force setting the value in the next evaluation (that's at the end of the function)
                    # and also update input nodes
                    self.update_input_nodes()
                    break

        if self.connected_node is not None:
            # AAARGH
            # set/get var nodes might create cycles in the node graph!! and fuck up has_changed semantics
            # especially with ChooseTexture
            # workaround for now: force update of float vars each time!
            if self.FORCE_UPDATE or self._force_value_update:
                self.set("output", self.connected_node.value)
                self._force_value_update = False
            else:
                # TODO clean this up!!
                # this thing is *slightly* faster
                if self.connected_node.value_has_changed:
                    self.set("output", self.connected_node.value)
                #self.connected_node.get_input("input").copy_to(self.get_output("output"))

        if input_name_changed:
            # see above where connected node is associated
            self._force_value_update = True

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
    FORCE_UPDATE = True

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

