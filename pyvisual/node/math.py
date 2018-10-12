from pyvisual.node.base import Node
from pyvisual.node import dtype
from pyvisual.editor import widget
import imgui

# as test for lambdas
import numpy as np
import math
import time

class AddFloat(Node):
    class Meta:
        inputs = [
            {"name" : "v0", "dtype" : dtype.float, "widgets" : [widget.Float]},
            {"name" : "v1", "dtype" : dtype.float, "widgets" : [widget.Float]}
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float, "widgets" : [widget.Float]}
        ]
        options = {
            "category" : "math",
        }

    def _evaluate(self):
        self.outputs["output"].value = self.inputs["v0"].value + self.inputs["v1"].value

class Or(Node):
    class Meta:
        inputs = [
            {"name" : "v0", "dtype" : dtype.bool, "widgets" : [widget.Bool]},
            {"name" : "v1", "dtype" : dtype.bool, "widgets" : [widget.Bool]}
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.event, "widgets" : [widget.Button]}
        ]
        options = {
            "category" : "math",
        }

    def _evaluate(self):
        v = self.get("v0") or self.get("v1")
        self.set("output", 1.0 if v else 0.0)
        self.changed = self.inputs["v0"].has_changed, self.inputs["v1"].has_changed

class And(Node):
    class Meta:
        inputs = [
            {"name" : "v0", "dtype" : dtype.bool, "widgets" : [widget.Bool]},
            {"name" : "v1", "dtype" : dtype.bool, "widgets" : [widget.Bool]}
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.bool, "widgets" : [widget.Bool]}
        ]
        options = {
            "category" : "math",
        }

    def _evaluate(self):
        v = self.get("v0") and self.get("v1")
        self.set("output", 1.0 if v else 0.0)
        self.changed = self.inputs["v0"].has_changed, self.inputs["v1"].has_changed

class Not(Node):
    class Meta:
        inputs = [
            {"name" : "v", "dtype" : dtype.bool, "widgets" : [widget.Bool]},
        ]
        outputs= [
            {"name" : "output", "dtype" : dtype.bool, "widgets" : [widget.Bool]},
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
            {"name" : "mode", "dtype" : dtype.int, "widgets" : [lambda node: widget.Choice(node, choices=COMPARE_MODES)]},
            {"name" : "v0", "dtype" : dtype.float, "widgets" : [widget.Float]},
            {"name" : "v1", "dtype" : dtype.float, "widgets" : [widget.Float]},
            {"name" : "threshold", "dtype" : dtype.float, "widgets" : [widget.Float]}
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.bool, "widgets" : [widget.Bool]}
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

THRESHOLD_MODES = ["rising", "falling", "both"]
class Threshold(Node):
    class Meta:
        inputs = [
            {"name" : "mode", "dtype" : dtype.int, "widgets" : [lambda node: widget.Choice(node, choices=THRESHOLD_MODES)]},
            {"name" : "value", "dtype" : dtype.float, "widgets" : [widget.Float]},
            {"name" : "threshold", "dtype" : dtype.float, "widgets" : [widget.Float]}
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.event, "widgets" : [widget.Button]}
        ]
        options = {
            "category" : "math",
        }

    def __init__(self):
        super().__init__()
        self.last_value = 0.0

    def _evaluate(self):
        mode = int(self.get("mode"))
        if mode < 0 or mode >= len(THRESHOLD_MODES):
            self.set("output", 0.0)
            return
        mode = THRESHOLD_MODES[mode]
        last_value = self.last_value
        value = self.get("value")
        threshold = self.get("threshold")
        if last_value < threshold and value >= threshold and (mode in ("rising", "both")):
            self.set("output", 1.0)
        elif last_value > threshold and value <= threshold and (mode in ("falling", "both")):
            self.set("output", 1.0)
        else:
            self.set("output", 0.0)
        self.last_value = value

class Lambda(Node):
    class Meta:
        options = {
            "virtual" : True,
        }

    def __init__(self):
        super().__init__()

        self.function = lambda x: x
        self.function_text = "x"
        self.text_changed = False
        self.compiles = True

        self.error = False
        self.last_try = 0

    def process_result(self, result):
        return result

    def _evaluate(self):
        try:
            self.set("output", self.process_result(self.function(self.inputs["input"].value)))
        except:
            self.error = True

    def _show_custom_ui(self):
        imgui.dummy(1, 5)
        imgui.text("lambda x:")
        imgui.push_item_width(208)
        changed, text = imgui.input_text("", self.function_text, 255, imgui.INPUT_TEXT_ENTER_RETURNS_TRUE)
        if changed or (self.error and time.time() - self.last_try > 1.0):
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
            {"name" : "input", "dtype" : dtype.float, "widgets" : [widget.Float]},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float, "widgets" : [widget.Float]}
        ]
        options = {
            "category" : "math",
        }

class ColorLambda(Lambda):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.color, "widgets" : [widget.Color]},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.color, "widgets" : [widget.Color]}
        ]
        options = {
            "category" : "math",
        }

    def process_result(self, result):
        if not isinstance(result, np.ndarray) or result.shape != (4,):
            raise RuntimeError("Invalid result. Must be (4,) array.")
        return result.astype(np.float32)
