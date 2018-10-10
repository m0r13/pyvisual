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
            {"name" : "type", "dtype" : dtype.int,  "widgets" : [widget.Choice(choices=list(LFO_OSCILLATORS.keys()))],  "default" : 2},
            {"name" : "length", "dtype" : dtype.float, "widgets" : [widget.Float()], "default" : 1.0},
            {"name" : "phase", "dtype" : dtype.float, "widgets" : [widget.Float()], "default" : 0.0},
            {"name" : "min", "dtype" : dtype.float, "widgets" : [widget.Float()], "default" : 0.0},
            {"name" : "max", "dtype" : dtype.float, "widgets" : [widget.Float()], "default" : 1.0},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float, "widgets" : [widget.Float()]}
        ]
        options = {
            "category" : "generate",
            "show_title" : True
        }

    def evaluate(self):
        generator = self.get("type")
        value = LFO.OSCILLATORS[generator](time.time(), self.get("length"), self.get("phase"))
        value = self.get("min") + value * (self.get("max") - self.get("min"))
        self.set("output", value)

