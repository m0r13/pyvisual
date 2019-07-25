import clipboard
import imgui
import numpy as np
import random

from pyvisual.node.base import Node, input_value_property
from pyvisual.node import dtype

class InputXXX(Node):
    class Meta:
        outputs = [
            #{"name" : "output", "dtype" : dtype.bool, "manual_input" : True}
        ]
        options = {
            "virtual" : True,
        }


    @classmethod
    def create_class(cls, name, dt, extra_inputs=[], extra_outputs=[]):
        class Meta:
            inputs = [
                {"name" : "input", "dtype" : dt},
                {"name" : "midi_mapping", "dtype" : dtype.obj, "hide" : True},
                {"name" : "name", "dtype" : dtype.str, "group" : "additional"},
                {"name" : "enable_randomization", "dtype" : dtype.bool, "dtype_args" : {"default" : False}, "group" : "additional"},
                {"name" : "default", "dtype" : dt, "group" : "additional"}
            ] + extra_inputs
            outputs = [
                {"name" : "output", "dtype" : dt, "hide_widget" : True}
            ] + extra_outputs
            options = {
                "virtual" : False,
            }

        return type(name, (cls,), {"DTYPE" : dt, "Meta" : Meta, "__module__" : __name__})

    def __init__(self, always_evaluate=False):
        super().__init__(always_evaluate=always_evaluate)

    def start(self, graph):
        super().start(graph)

        #self.get_input("midi_mapping").value = None

    @property
    def node_title(self):
        return "I: %s" % self.get("name")

    @property
    def name(self):
        return self.get("name")

    midi_mapping = input_value_property("midi_mapping")
    enable_randomization = input_value_property("enable_randomization")

    def get_absolute_value(self, value):
        raise NotImplemented()
    def set_absolute_value(self, value):
        raise NotImplemented()

    def set_offset_value(self, offset):
        self._set_value(self._get_random_value())

    def set_random_value(self, force=1.0):
        if self.enable_randomization and random.random() <= force:
            self._set_value(self._get_random_value())

    def _get_value(self):
        return self.get_value("i_input").value
    def _set_value(self, value):
        self.get_value("i_input").value = value

    def _get_random_value(self):
        return self.get("default")

    def _evaluate(self):
        self.get_input("input").copy_to(self.get_output("output"))
        #self.set("output", self.get("input"))

    def _show_custom_context(self):
        if imgui.button("set default value"):
            self._set_value(self.get("default"))

# TODO actually handle clamping on input value
#    - manipulate port spec, but also change value?!
# or - have custom port, how does it handle current value and re-creating values?
class ClampedInputXXX(InputXXX):
    class Meta:
        options = {
            "virtual" : True,
        }

    @classmethod
    def create_class(cls, name, dt):
        extra_inputs = [
            {"name" : "min", "dtype" : dt, "dtype_args" : {"default" : float("-inf")}, "group" : "additional"},
            {"name" : "max", "dtype" : dt, "dtype_args" : {"default" : float("inf")}, "group" : "additional"},
            {"name" : "step", "dtype" : dt, "dtype_args" : {"default" : 1.0}, "group" : "additional"},
            {"name" : "base", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0, "range" : [0.001, float("inf")]}, "group" : "additional"}
        ]
        return super().create_class(name, dt, extra_inputs=extra_inputs)

    def get_relative_value(self):
        alpha = (self._get_value() - self.get("min")) / (self.get("max") - self.get("min"))
        return alpha
    def set_relative_value(self, alpha):
        alpha = alpha ** self.get("base")
        self._set_value(self.get("min") * (1.0 - alpha) + self.get("max") * alpha)

    def set_offset_value(self, offset):
        self._set_value(self._get_value() + offset * self.get("step"))

    def _get_random_value(self):
        if self.__class__ == InputInt:
            return random.randint(self.get("min"), self.get("max"))
        else:
            alpha = random.random()
            return (1.0 - alpha) * self.get("min") + alpha * self.get("max")

    def _evaluate(self):
        super()._evaluate()

        r = [self.get("min"), self.get("max")]

        port_spec = self.get_port("i_input")
        port_spec["dtype_args"] = {"range" : r}
        if "o_default" in self.values:
            v = self.values["i_input"].value
            self.initial_manual_values["i_input"] = v
            del self.values["i_input"]

    def _show_custom_context(self):
        super()._show_custom_context()

        if imgui.button("min=-Infinity"):
            self.get_input("min").value = float("-inf")
        imgui.same_line()
        if imgui.button("max=Infinity"):
            self.get_input("max").value = float("inf")

InputInt = ClampedInputXXX.create_class("InputInt", dtype.int)
InputFloat = ClampedInputXXX.create_class("InputFloat", dtype.float)

# InputString

class InputBool(InputXXX):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.bool},
            {"name" : "midi_mapping", "dtype" : dtype.obj, "hide" : True},
            {"name" : "name", "dtype" : dtype.str, "group" : "additional"},
            {"name" : "enable_randomization", "dtype" : dtype.bool, "dtype_args" : {"default" : False}, "group" : "additional"},
            {"name" : "default", "dtype" : dtype.bool, "group" : "additional"},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.bool, "hide_widget" : True}
        ]
        options = {
        }

    def get_relative_value(self):
        return self._get_value()
    def set_relative_value(self, alpha):
        self._set_value(alpha >= 0.5)

    def set_offset_value(self, offset):
        self._set_value((self._get_value() + offset) % 2)

    def _get_random_value(self):
        #return random.random() > 0.5
        return not self._get_value()

class InputEvent(InputXXX):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.event, "manual_input" : True},
            {"name" : "midi_mapping", "dtype" : dtype.obj, "hide" : True},
            {"name" : "name", "dtype" : dtype.str, "group" : "additional"},
            {"name" : "enable_randomization", "dtype" : dtype.bool, "dtype_args" : {"default" : False}, "group" : "additional"},
            {"name" : "default", "dtype" : dtype.event, "hide" : True, "group" : "additional"},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.event, "hide_widget" : True}
        ]
        options = {
        }

    def __init__(self):
        super().__init__(always_evaluate=True)

        self._was_on = False

    def start(self, graph):
        self._set_value(0.0)

    def get_relative_value(self):
        return self._get_value()
    def set_relative_value(self, alpha):
        self._set_value(alpha)

    def _evaluate(self):
        #super()._evaluate()

        v = self.get("input")
        #print("i:", v, self._was_on)
        if v and self._was_on:
            self._was_on = False
            v = 0.0
        if v:
            self._was_on = True
        self._set_value(v)
        self.set("output", v)
        #print("o:", v, self._was_on)

    def set_offset_value(self, offset):
        self._set_value((self._get_value() + offset) % 2)

class InputChoice(InputXXX):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.int, "manual_input" : True},
            {"name" : "midi_mapping", "dtype" : dtype.obj, "hide" : True},
            {"name" : "name", "dtype" : dtype.str, "group" : "additional"},
            {"name" : "enable_randomization", "dtype" : dtype.bool, "dtype_args" : {"default" : False}, "group" : "additional"},
            {"name" : "default", "dtype" : dtype.int, "group" : "additional"},
            {"name" : "choices", "dtype" : dtype.str, "group" : "additional", "dtype_args": {"variant" : "text"}},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.int, "hide_widget" : True}
        ]
        options = {
        }

    def __init__(self):
        super().__init__()

        self._choices = []

    def _set_value(self, value):
        if len(self._choices) == 0:
            super()._set_value(0)
            return

        super()._set_value(value % len(self._choices))

    def set_relative_value(self, alpha):
        choices = len(self._choices)
        if choices > 0:
            choices -= 1
        self._set_value(alpha * choices)

    def set_offset_value(self, offset):
        self._set_value(self._get_value() + offset * 0.5)

    def _get_random_value(self):
        if len(self._choices) == 0:
            return 0
        return random.randint(0, len(self._choices) - 1)

    def _evaluate(self):
        super()._evaluate()

        self._choices = self.get("choices").strip().split("\n")
        if len(self._choices) == 0:
            self._set_value(0)
            return

        port_spec = self.get_port("i_default")
        port_spec["dtype_args"] = {"choices" : self._choices}
        if "i_default" in self.values:
            v = self.get("default")
            self.initial_manual_values["i_default"] = v
            del self.values["i_default"]

        port_spec = self.get_port("i_input")
        port_spec["dtype_args"] = {"choices" : self._choices}
        if "i_input" in self.values:
            v = self.values["i_input"].value
            self.initial_manual_values["i_input"] = v
            del self.values["i_input"]

        port_spec = self.get_port("o_output")
        port_spec["dtype_args"] = {"choices" : self._choices}
        if "o_default" in self.values:
            v = self.values["o_output"].value
            self.initial_manual_values["o_output"] = v
            del self.values["o_output"]

    def _show_custom_context(self):
        super()._show_custom_context()

        if imgui.button("paste choices"):
            self.get_input("choices").value = clipboard.paste()

#class InputBool(Node):
#    class Meta:
#        outputs = [
#            {"name" : "output", "dtype" : dtype.bool, "manual_input" : True}
#        ]
#        options = {
#            "category" : "input",
#            "show_title" : False
#        }

#class OutputBool(Node):
#    class Meta:
#        inputs = [
#            {"name" : "input", "dtype" : dtype.bool, "manual_input" : False}
#        ]
#        options = {
#            "category" : "output",
#            "show_title" : False
#        }

#class InputEvent(Node):
#    class Meta:
#        outputs = [
#            {"name" : "output", "dtype" : dtype.event, "manual_input" : True}
#        ]
#        options = {
#            "category" : "input",
#            "show_title" : False
#        }

#class OutputEvent(Node):
#    class Meta:
#        inputs = [
#            {"name" : "input", "dtype" : dtype.event, "manual_input" : False}
 #       ]
 ##       options = {
#            "category" : "output",
#            "show_title" : False
#        }

#class InputInt(Node):
#    class Meta:
#        outputs = [
#            {"name" : "output", "dtype" : dtype.int, "manual_input" : True}
#        ]
#        options = {
#            "category" : "input",
#            "show_title" : False
#        }
#
#class OutputInt(Node):
#    class Meta:
#        inputs = [
#            {"name" : "input", "dtype" : dtype.int, "manual_input" : False}
#        ]
#        options = {
#            "category" : "output",
#            "show_title" : False
#        }

#class InputFloat(Node):
#    class Meta:
#        outputs = [
#            {"name" : "output", "dtype" : dtype.float, "manual_input" : True}
#        ]
#        options = {
#            "category" : "input",
#            "show_title" : False
#        }

#class OutputFloat(Node):
#    class Meta:
#        inputs = [
#            {"name" : "input", "dtype" : dtype.float, "manual_input" : False}
#        ]
#        options = {
#            "category" : "output",
#            "show_title" : False
#        }

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

