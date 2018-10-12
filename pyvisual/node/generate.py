import time
import math
from collections import OrderedDict
from pyvisual.node.base import Node
from pyvisual.node import dtype
from pyvisual.editor import widget

LFO_OSCILLATORS = OrderedDict(
    square=lambda t, length, phase: float(math.fmod(t - phase, length) < 0.5 * length),
    saw=lambda t, length, phase: float(2.0 / math.pi * math.atan(math.tan((2*math.pi*t - phase) / length))) * 0.5 + 0.5,
    triangle=lambda t, length, phase: float(2.0 / math.pi * math.asin(math.sin((2*math.pi*t - phase) / length))) * 0.5 + 0.5,
    sine=lambda t, length, phase: math.sin((2*math.pi*t - phase) / length) * 0.5 + 0.5
)

class LFO(Node):
    OSCILLATORS = list(LFO_OSCILLATORS.values())

    class Meta:
        inputs = [
            {"name" : "type", "dtype" : dtype.int,  "widgets" : [lambda node: widget.Choice(node, choices=list(LFO_OSCILLATORS.keys()))],  "default" : 2},
            {"name" : "length", "dtype" : dtype.float, "widgets" : [lambda node: widget.Float(node, minmax=[0.0001, float("inf")])], "default" : 1.0},
            {"name" : "phase", "dtype" : dtype.float, "widgets" : [widget.Float], "default" : 0.0},
            {"name" : "min", "dtype" : dtype.float, "widgets" : [widget.Float], "default" : 0.0},
            {"name" : "max", "dtype" : dtype.float, "widgets" : [widget.Float], "default" : 1.0},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float, "widgets" : [widget.Float]}
        ]
        options = {
            "category" : "generate",
            "show_title" : True
        }

    def __init__(self):
        super().__init__(always_evaluate=True)

    def _evaluate(self):
        generator = self.get("type")
        length = self.get("length")
        if length == 0:
            self.set("output", float("nan"))
            return
        value = LFO.OSCILLATORS[generator](time.time(), self.get("length"), self.get("phase"))
        value = self.get("min") + value * (self.get("max") - self.get("min"))
        self.set("output", value)

class Time(Node):
    class Meta:
        inputs = [
            {"name" : "reset", "dtype" : dtype.event, "widgets" : [widget.Button]}
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float, "widgets" : [widget.Float]}
        ]
        options = {
            "category" : "generate",
            "show_title" : True
        }

    def __init__(self):
        super().__init__(always_evaluate=True)

        self._start = time.time()

    def _evaluate(self):
        if self.get("reset"):
            self._start = time.time()
        self.set("output", time.time() - self._start)
