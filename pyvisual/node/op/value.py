import imgui
import numpy as np
import time
import math
import random
import colorsys
from collections import OrderedDict
from scipy import signal

from pyvisual.node.base import Node
from pyvisual.node import dtype
from pyvisual.editor import widget
from pyvisual.audio import util

from glumpy.app import clock

#
# Base operation nodes
#

class Latch(Node):
    class Meta:
        inputs = [
            {"name" : "enabled", "dtype" : dtype.bool, "dtype_args" : {"default" : True}}
        ]
        options = {
            "virtual" : True
        }

    def _evaluate(self):
        if self.get("enabled"):
            self.set("output", self.get("input"))

class Lambda(Node):
    class Meta:
        inputs = [
            {"name" : "lambda", "dtype" : dtype.str, "dtype_args" : {"default" : "x"}, "hide" : True},
        ]
        options = {
            "virtual" : True,
        }

    def __init__(self):
        super().__init__()

        self.function = lambda x: x
        self.compile_error = None
        self.run_error = None

    def process_result(self, result):
        return result

    def build_lambda(self):
        try:
            function = eval("lambda x: %s" % self.get("lambda"))
            self.function = function
            self.compile_error = None
        except Exception as e:
            self.compile_error = str(e)

    def _evaluate(self):
        if self.have_inputs_changed("lambda"):
            self.build_lambda()

        try:
            self.set("output", self.process_result(self.function(self.get("input"))))
            self.run_error = None
        except Exception as e:
            self.run_error = str(e)

    def _show_custom_ui(self):
        imgui.dummy(1, 5)
        imgui.text("lambda x:")
        imgui.push_item_width(208)
        changed, text = imgui.input_text("", self.get("lambda"), 255, imgui.INPUT_TEXT_ENTER_RETURNS_TRUE)
        if changed:
            self.get_input("lambda").value = text

        if self.compile_error is not None:
            imgui.text_colored("Compilation error. (?)", 1.0, 0.0, 0.0)
            if imgui.is_item_hovered():
                imgui.set_tooltip(self.compile_error)
        elif self.run_error is not None:
            imgui.text_colored("Runtime error. (?)", 1.0, 0.0, 0.0)
            if imgui.is_item_hovered():
                imgui.set_tooltip(self.run_error)
        else:
            imgui.text("Lambda compiled.")

#
# Bool operations
#

class Or(Node):
    class Meta:
        inputs = [
            {"name" : "v0", "dtype" : dtype.bool},
            {"name" : "v1", "dtype" : dtype.bool}
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.bool}
        ]
        options = {
            "category" : "math",
        }

    def _evaluate(self):
        v = self.get("v0") or self.get("v1")
        self.set("output", 1.0 if v else 0.0)

class And(Node):
    class Meta:
        inputs = [
            {"name" : "v0", "dtype" : dtype.bool},
            {"name" : "v1", "dtype" : dtype.bool}
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.bool}
        ]
        options = {
            "category" : "math",
        }

    def _evaluate(self):
        v = self.get("v0") and self.get("v1")
        self.set("output", 1.0 if v else 0.0)

class Not(Node):
    class Meta:
        inputs = [
            {"name" : "v", "dtype" : dtype.bool},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.bool},
        ]
        options = {
            "category" : "math",
        }

    def _evaluate(self):
        v = self.get("v")
        self.set("output", 0.0 if v else 1.0)

#
# Float operations
#

COMPARE_MODES = ["v0 < v1", "v0 <= v1", "v0 > v1", "v0 >= v1", "v0 == v1"]
class Compare(Node):
    class Meta:
        inputs = [
            {"name" : "mode", "dtype" : dtype.int, "dtype_args" : {"choices" : COMPARE_MODES}},
            {"name" : "v0", "dtype" : dtype.float},
            {"name" : "v1", "dtype" : dtype.float},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.bool}
        ]
        options = {
            "category" : "math",
        }

    def _evaluate(self):
        mode = int(self.get("mode"))
        v0 = self.get("v0")
        v1 = self.get("v1")
        value = (mode == 0 and v0 < v1) \
             or (mode == 1 and v0 <= v1) \
             or (mode == 2 and v0 > v1) \
             or (mode == 3 and v0 >= v1) \
             or (mode == 4 and abs(v0 - v1) < 0.0001)
        self.set("output", 1.0 if value else 0.0)

class Edge(Node):
    class Meta:
        inputs = [
            {"name" : "value", "dtype" : dtype.float},
            {"name" : "threshold", "dtype" : dtype.float}
        ]
        outputs = [
            {"name" : "rising", "dtype" : dtype.event},
            {"name" : "falling", "dtype" : dtype.event},
            {"name" : "combined", "dtype" : dtype.event}
        ]
        options = {
            "category" : "math"
        }

    def __init__(self):
        super().__init__(always_evaluate=True)
        self.last_value = 0.0

    def _evaluate(self):
        last_value = self.last_value
        value = self.get("value")
        threshold = self.get("threshold")
        self.set("rising", last_value < threshold and value >= threshold)
        self.set("falling", last_value >= threshold and value < threshold)
        self.set("combined", last_value < threshold and value >= threshold or last_value > threshold and value <= threshold)
        self.last_value = value

class BoolEdge(Node):
    class Meta:
        inputs = [
            {"name" : "value", "dtype" : dtype.bool},
        ]
        outputs = [
            {"name" : "rising", "dtype" : dtype.event},
            {"name" : "falling", "dtype" : dtype.event},
            {"name" : "combined", "dtype" : dtype.event}
        ]
        options = {
            "category" : "math"
        }

    def __init__(self):
        super().__init__(always_evaluate=True)
        self.last_value = 0.0

    def _evaluate(self):
        last_value = self.last_value
        value = self.get("value")

        rising = not last_value and value
        falling = last_value and not value
        self.set("rising", rising)
        self.set("falling", falling)
        self.set("combined", rising or falling)
        self.last_value = value


class FloatLatch(Latch):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.float}
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float}
        ]
        options = {
            "virtual" : False,
            "category" : "math"
        }

class MixFloat(Node):
    class Meta:
        inputs = [
            {"name" : "a", "dtype" : dtype.float},
            {"name" : "b", "dtype" : dtype.float},
            {"name" : "alpha", "dtype" : dtype.float, "dtype_args" : {}},
            {"name" : "alpha0", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}, "group" : "additional"},
            {"name" : "alpha1", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}, "group" : "additional"},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float}
        ]
        options = {
            "category" : "math"
        }

    def _evaluate(self):
        alpha = self.get("alpha")
        alpha0 = self.get("alpha0")
        alpha1 = self.get("alpha1")
        if alpha1 - alpha0 != 0.0:
            alpha = (alpha - alpha0) / (alpha1 - alpha0)
        else:
            alpha = float("nan")

        a = self.get("a")
        b = self.get("b")
        self.set("output", (1.0-alpha) * a + alpha * b)

UNARY_OPS = OrderedDict(
    id=lambda x: x,
    abs=lambda x: abs(x),
    neg=lambda x: -x,
    oneminus=lambda x: 1.0 - x,
)

UNARY_OP_PRESETS = [
    (name, {"i_op" : i}) for i, name in enumerate(UNARY_OPS.keys())
]

class UnaryOpFloat(Node):
    class Meta:
        inputs = [
            {"name" : "op", "dtype" : dtype.int, "dtype_args" : {"choices" : list(UNARY_OPS.keys())}},
            {"name" : "x", "dtype" : dtype.float},
        ]
        outputs = [
            {"name" : "out", "dtype" : dtype.float}
        ]
        options = {
            "show_title" : False
        }

    OPS = list(UNARY_OPS.values())

    def __init__(self):
        super().__init__()

        self._op_name = ""
        self._op = None

    @property
    def descriptive_title(self):
        return "op: %s" % self._op_name

    def _evaluate(self):
        op_value = self.get_input("op")
        if op_value.has_changed:
            op = int(op_value.value)
            if op < 0 or op >= len(self.OPS):
                op = 0
            self._op_name = list(UNARY_OPS.keys())[op]
            self._op = self.OPS[op]

        x = self.get("x")
        self.set("out", self._op(x))

    @classmethod
    def get_presets(cls, graph):
        return UNARY_OP_PRESETS

BINARY_OPS = OrderedDict(
    add=lambda a, b: a + b,
    sub=lambda a, b: a - b,
    mul=lambda a, b: a * b,
    div=lambda a, b: a / b,

    min=lambda a, b: min(a, b),
    max=lambda a, b: max(a, b),

    divmod=lambda a, b: a - (a % b),

    pow=lambda a, b: a**b
)

BINARY_OP_PRESETS = [
    (name, {"i_op" : i}) for i, name in enumerate(BINARY_OPS.keys())
]

class BinaryOpFloat(Node):
    class Meta:
        inputs = [
            {"name" : "op", "dtype" : dtype.int, "dtype_args" : {"choices" : list(BINARY_OPS.keys())}},
            {"name" : "a", "dtype" : dtype.float},
            {"name" : "b", "dtype" : dtype.float},
        ]
        outputs = [
            {"name" : "out", "dtype" : dtype.float}
        ]
        options = {
            "show_title" : False
        }

    OPS = list(BINARY_OPS.values())

    def __init__(self):
        super().__init__()

        self._op_name = ""
        self._op = None

    @property
    def descriptive_title(self):
        return "op: %s" % self._op_name

    def _evaluate(self):
        op_value = self.get_input("op")
        if op_value.has_changed:
            op = int(op_value.value)
            if op < 0 or op >= len(self.OPS):
                op = 0
            self._op_name = list(BINARY_OPS.keys())[op]
            self._op = self.OPS[op]

        a = self.get("a")
        b = self.get("b")
        try:
            self.set("out", self._op(a, b))
        except ZeroDivisionError:
            self.set("out", float("nan"))

    @classmethod
    def get_presets(cls, graph):
        return BINARY_OP_PRESETS

# TODO find consistent naming for these
def state_initial_value(node):
    # TODO this is a hack
    # if set_initial_state is called as of yet there is no value set yet
    # just return the default value 0.0 then
    # if a graph is loaded from a file, the state is set accordingly later anyways
    if "i_reset_value" in node.values:
        return node.get("reset_value")
    return 0.0

class Counter(Node):
    class Meta:
        inputs = [
            {"name" : "op", "dtype" : dtype.int, "dtype_args" : {"choices" : list(BINARY_OPS.keys())}},
            {"name" : "operand", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "operate", "dtype" : dtype.event},
            {"name" : "reset", "dtype" : dtype.event},
            {"name" : "reset_value", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
        ]
        outputs = [
            {"name" : "out", "dtype" : dtype.float}
        ]
        initial_state = {
            "value" : state_initial_value
        }
        random_state = {
            "value" : state_initial_value
        }

    OPS = list(BINARY_OPS.values())

    def __init__(self):
        super().__init__()

    def _evaluate(self):
        if self.get("reset"):
            self.reset_state()

        if self.get("operate"):
            op = int(self.get("op"))
            if op < 0 or op >= len(self.OPS):
                op = 0

            a = self._value
            b = self.get("operand")
            self._value = self.OPS[op](a, b)

        self.set("out", self._value)

    def get_state(self):
        return {"value" : self._value}

    def set_state(self, state):
        if "value" in state:
            self._value = state["value"]

class FloatLambda(Lambda):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.float},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float}
        ]
        options = {
            "category" : "math",
            "virtual" : False
        }

class LowpassFloat(Node):
    class Meta:
        inputs = [
            {"name" : "enabled", "dtype" : dtype.bool, "dtype_args" : {"default" : True}},
            {"name" : "input", "dtype" : dtype.float},
            {"name" : "order", "dtype" : dtype.int, "dtype_args" : {"default" : 2, "range" : [0, float("inf")]}},
            # TODO fps automatically!
            {"name" : "cutoff", "dtype" : dtype.float, "dtype_args" : {"default" : 2.5, "range" : [0.00001, 60.0 / 2.0 - 0.00001]}},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float},
        ]

    def __init__(self):
        super().__init__(always_evaluate=True)

        self._filter = None
        self.status = None

    def _create_filter(self, order, cutoff):
        try:
            fps = clock.get_default().get_fps_limit() * 0.75
            filter = util.Filter(signal.butter, order, cutoff, fps, {"btype" : "low", "analog" : False})
            self.status = None
            return filter
        except ValueError as e:
            self.status = str(e)

    def _evaluate(self):
        if self.have_inputs_changed("order", "cutoff") or self._last_evaluated == 0.0:
            self._filter = self._create_filter(self.get("order"), self.get("cutoff"))

        value = self.get("input")
        if self._filter:
            filtered = self._filter.process(np.array([value]))[0]
            self.set("output", filtered if self.get("enabled") else value)
        else:
            self.set("output", value)

    def _show_custom_ui(self):
        if self.status:
            imgui.dummy(1, 5)
            imgui.text_colored("Error. (?)", 1.0, 0.0, 0.0)
            if imgui.is_item_hovered():
                imgui.set_tooltip(self.status)

class SetResetToggle(Node):
    class Meta:
        inputs = [
            {"name" : "v0", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "v1", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "set", "dtype" : dtype.event},
            {"name" : "reset", "dtype" : dtype.event},
            {"name" : "toggle", "dtype" : dtype.event},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float},
        ]
        initial_state = {
            "value" : False
        }
        random_state = {
            "value" : lambda node: bool(random.randint(0, 1))
        }

    def __init__(self):
        super().__init__()

    def _evaluate(self):
        if not self._value and self.get("set"):
            self._value = True
        if self._value and self.get("reset"):
            self._value = False
        if self.get("toggle"):
            self._value = not self._value

        self.set("output", self.get("v1") if self._value else self.get("v0"))

    def get_state(self):
        return {"value" : self._value}

    def set_state(self, state):
        if "value" in state:
            self._value = state["value"]

#
# Vec2 operations
#

class RotatedVec2(Node):
    class Meta:
        inputs = [
            {"name" : "length", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "angle", "dtype" : dtype.float},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.vec2}
        ]

    def _evaluate(self):
        angle = math.radians(self.get("angle"))
        cos = math.cos(angle)
        sin = math.sin(angle)
        v = np.float32([self.get("length"), 0])
        rot = np.float32([[cos, -sin],
                          [sin, cos]])
        self.set("output", v.dot(rot))

#
# Color operations
#

class ColorLatch(Latch):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.color}
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.color}
        ]
        options = {
            "virtual" : False,
            "category" : "math"
        }

class ColorLambda(Lambda):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.color},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.color}
        ]
        options = {
            "category" : "math",
            "virtual" : False
        }

    def process_result(self, result):
        if not isinstance(result, np.ndarray) or result.shape != (4,):
            raise RuntimeError("Invalid result. Must be (4,) array.")
        return result.astype(np.float32)

class HSV2RGBA(Node):
    class Meta:
        inputs = [
            {"name" : "h", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "s", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "v", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "a", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0, "range" : [0.0, 1.0]}},
        ]
        outputs = [
            {"name" : "rgba", "dtype" : dtype.color}
        ]

    def _evaluate(self):
        # vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
        # vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
        # return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);

        h, s, v = self.get("h"), self.get("s"), self.get("v")
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        self.set("rgba", np.float32([r, g, b, self.get("a")]))

#
# Texture operations
#

from glumpy import gloo

class HoldTexture(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.tex2d},
            {"name" : "hold", "dtype" : dtype.event},
            ]
        outputs = [
            {"name" : "output", "dtype" : dtype.tex2d},
        ]

    def __init__(self):
        super().__init__()

        self._texture = None

    def _evaluate(self):
        if self.get("hold"):
            texture = self.get("input")
            if texture is None:
                self._texture = None
            else:
                # take detour by CPU for now
                # - as glumpy doesn't make it so easy to copy texture data
                t = texture.get().copy().view(gloo.Texture2D)
                t.activate()
                t.deactivate()
                self._texture = t
            self.set("output", self._texture)

#
# String operations
#

class ChooseString(Node):
    class Meta:
        inputs = [
            {"name" : "choices", "dtype" : dtype.str, "hide" : True},
            {"name" : "index", "dtype" : dtype.int, "dtype_args" : {"range" : [0, float("inf")]}},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.str}
        ]

    def __init__(self):
        super().__init__()

        self._choices = []

    def _evaluate(self):
        choices = self.get_input("choices")
        if choices.has_changed:
            self._choices = choices.value.strip().split("\n")

        i = int(self.get("index"))
        if i < 0 or i >= len(self._choices):
            i = max(0, min(len(self._choices) - 1, i))
            self.get_input("index").value = i
        self.set("output", self._choices[i])

    def _show_custom_context(self):
        changed, text = imgui.input_text_multiline("", self.get("choices"), 1024)
        if changed:
            self.get_input("choices").value = text

        super()._show_custom_context()

#
# Misc / Meta operations
#

# Delays a float value by one frame
# Always required for cyclic connections in the graph!
class DelayFloat(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.float}
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float}
        ]

    FORCE_EARLY_EXECUTION = True

    def __init__(self):
        super().__init__()

        # The value None has special meaning here: indicates that there is no next value.
        # Consequence: The value shouldn't take the value None!!
        self._next_value = None

    def _evaluate(self):
        if self._next_value is not None:
            self.set("output", self._next_value)
            self._next_value = None

    def _after_evaluate(self):
        # Called after evaluation of all nodes, changed values in the previous frame are forwarded like this!
        value = self.get_input("input")
        if value.has_changed:
            self._next_value = value.value
            self.force_evaluate()

