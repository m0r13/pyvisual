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
            {"name" : "output", "dtype" : dtype.event}
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

COMPARE_MODES = ["v0 < v1", "v0 <= v1", "v0 > v1", "v0 >= v1"]
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
             or (mode == 3 and v0 >= v1)
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
            {"name" : "alpha", "dtype" : dtype.float, "dtype_args" : {"range" : [0.0, 1.0]}}
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float}
        ]
        options = {
            "category" : "math"
        }

    def _evaluate(self):
        self.set("output", (1.0-self.get("alpha")) * self.get("a") + self.get("alpha") * self.get("b"))

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
    def collapsed_title(self):
        return "op: %s" % self._op_name

    def _evaluate(self):
        op_value = self.get_input("op")
        if op_value.has_changed:
            op = int(op_value)
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
    def collapsed_title(self):
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

    OPS = list(BINARY_OPS.values())

    def __init__(self):
        super().__init__()

        self._value = 0.0

    def _evaluate(self):
        if self.get("reset") or self._last_evaluated == 0.0:
            self._value = self.get("reset_value")

        if self.get("operate"):
            op = int(self.get("op"))
            if op < 0 or op >= len(self.OPS):
                op = 0

            a = self._value
            b = self.get("operand")
            self._value = self.OPS[op](a, b)

        self.set("out", self._value)

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

        self._filter = self._create_filter(self.get("order"), self.get("cutoff"))
        self.status = None

    def _create_filter(self, order, cutoff):
        try:
            filter = util.Filter(signal.butter, order, cutoff, 60, {"btype" : "low", "analog" : False})
            self.status = None
            return filter
        except ValueError as e:
            self.status = str(e)

    def _evaluate(self):
        if self.have_inputs_changed("order", "cutoff"):
            self._filter = self._create_filter(self.get("order"), self.get("cutoff"))

        value = self.get("input")
        if self._filter:
            self.set("output", self._filter.process(np.array([value]))[0])
        else:
            self.set("output", value)

    def _show_custom_ui(self):
        if self.status:
            imgui.dummy(1, 5)
            imgui.text_colored("Error. (?)", 1.0, 0.0, 0.0)
            if imgui.is_item_hovered():
                imgui.set_tooltip(self.status)

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
