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

    def evaluate(self):
        self.outputs["output"].value = self.inputs["v0"].value + self.inputs["v1"].value

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

    def evaluate(self):
        try:
            self.set("output", self.process_result(self.function(self.inputs["input"].value)))
        except:
            self.error = True

    def show_custom_ui(self):
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
            {"name" : "input", "dtype" : dtype.vec4, "widgets" : [widget.Color]},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.vec4, "widgets" : [widget.Color]}
        ]
        options = {
            "category" : "math",
        }

    def process_result(self, result):
        if not isinstance(result, np.ndarray) or result.shape != (4,):
            raise RuntimeError("Invalid result. Must be (4,) array.")
        return result.astype(np.float32)
