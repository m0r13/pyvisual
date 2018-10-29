from collections import OrderedDict
from pyvisual.node.base import Node
from pyvisual.node import dtype
from pyvisual.editor import widget
import imgui

# as test for lambdas
import numpy as np
import math
import time

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

# TODO maybe Compare and Threshold can combined somehow or so?

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
        super().__init__()
        self.last_value = 0.0

    def _evaluate(self):
        last_value = self.last_value
        value = self.get("value")
        threshold = self.get("threshold")
        self.set("rising", last_value < threshold and value >= threshold)
        self.set("falling", last_value > threshold and value <= threshold)
        self.set("combined", last_value < threshold and value >= threshold or last_value > threshold and value <= threshold)
        self.last_value = value

# TODO naming?
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

class BlendFloat(Node):
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

    def _evaluate(self):
        op = int(self.get("op"))
        if op < 0 or op >= len(self.OPS):
            op = 0

        x = self.get("x")
        self.set("out", self.OPS[op](x))

BINARY_OPS = OrderedDict(
    add=lambda a, b: a + b,
    sub=lambda a, b: a - b,
    mul=lambda a, b: a * b,
    div=lambda a, b: a / b,

    min=lambda a, b: min(a, b),
    max=lambda a, b: max(a, b),

    divmod=lambda a, b: a - (a % b)
)

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

    def _evaluate(self):
        op = int(self.get("op"))
        if op < 0 or op >= len(self.OPS):
            op = 0

        a = self.get("a")
        b = self.get("b")
        self.set("out", self.OPS[op](a, b))

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
        self.function_text = None
        self.text_changed = False
        self.compiles = True

        self.error = False
        self.last_try = 0

    def process_result(self, result):
        return result

    def _evaluate(self):
        try:
            self.set("output", self.process_result(self.function(self.get("input"))))
        except:
            self.error = True

    def _show_custom_ui(self):
        first_run = False
        if self.function_text is None:
            self.function_text = self.get("lambda")
            first_run = True

        imgui.dummy(1, 5)
        imgui.text("lambda x:")
        imgui.push_item_width(208)
        changed, text = imgui.input_text("", self.function_text, 255, imgui.INPUT_TEXT_ENTER_RETURNS_TRUE)
        self.get_input("lambda").manual_value.value = self.function_text
        if changed or first_run or (self.error and time.time() - self.last_try > 1.0):
            self.last_try = time.time()
            try:
                function = eval("lambda x: %s" % self.function_text)
                self.function = function
                self.text_changed = False
                self.compiles = True
                self.error = False
            except:
                self.compiles = False
        else:
            if text != self.function_text:
                self.text_changed = True
        self.function_text = text
        if not self.compiles:
            imgui.text("Compilation error.")
        elif self.error:
            imgui.text("Runtime error.")
        else:
            imgui.text("Lambda compiled." + (" (changed)" if self.text_changed else ""))

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

from pyvisual.audio import analyzer
class Plot(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.float},
            {"name" : "min", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "max", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "time", "dtype" : dtype.float, "dtype_args" : {"default" : 5.0}},
        ]
        options = {
            "category" : "math",
            "virtual" : False
        }

    def __init__(self):
        super().__init__(always_evaluate=True)
        self.buffer = analyzer.RingBuffer(5*60)

    def _evaluate(self):
        self.buffer.append(self.get("input"))

    def _show_custom_ui(self):
        imgui.plot_lines("", self.buffer.contents, float(self.get("min")), float(self.get("max")), (200, 50))
