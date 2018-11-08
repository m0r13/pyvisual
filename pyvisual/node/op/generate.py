import time
import math
import random
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

def scalable_timer():
    _last_time = time.time()
    _time = 0.0
    def _timer(scale, reset=False):
        nonlocal _last_time, _time
        t = time.time()
        if reset:
            _time = 0.0
        dt = t - _last_time
        _time += dt * scale
        _last_time = t
        return _time
    return _timer

class LFO(Node):
    OSCILLATORS = list(LFO_OSCILLATORS.values())

    class Meta:
        inputs = [
            {"name" : "type", "dtype" : dtype.int, "dtype_args" : {"default" : 2, "choices" : list(LFO_OSCILLATORS.keys())}},
            {"name" : "length", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0, "range" : [0.000001, float("inf")]}},
            {"name" : "phase", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "min", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "max", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float}
        ]
        options = {
            "category" : "generate",
            "show_title" : True
        }

    def __init__(self):
        super().__init__(always_evaluate=True)

        self.timer = scalable_timer()

    def _evaluate(self):
        generator = int(self.get("type"))
        length = self.get("length")
        if length == 0:
            self.set("output", float("nan"))
            return
        t = self.timer(1.0 / self.get("length"), False)
        value = LFO.OSCILLATORS[generator](t, 1.0 + 0.0 * self.get("length"), self.get("phase"))
        value = self.get("min") + value * (self.get("max") - self.get("min"))
        self.set("output", value)

class Time(Node):
    class Meta:
        inputs = [
            {"name" : "factor", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "reset", "dtype" : dtype.event}
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float}
        ]
        options = {
            "category" : "generate",
            "show_title" : True
        }

    def __init__(self):
        super().__init__(always_evaluate=True)

        self._last_time = time.time()
        self._time = 0.0

    def _evaluate(self):
        t = time.time()
        if self.get("reset"):
            self._time = 0.0
        dt = t - self._last_time
        self._time += dt * self.get("factor")
        self._last_time = t
        self.set("output", self._time)

def random_float(a, b):
    alpha = random.random()
    value = a * (1.0-alpha) + b * alpha
    return value

class RandomFloat(Node):
    class Meta:
        inputs = [
            {"name" : "generate", "dtype" : dtype.event},
            {"name" : "min", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "max", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "mod", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float}
        ]
        options = {
            "category" : "generate",
            "show_title" : True
        }

    def _evaluate(self):
        if self.get("generate"):
            min_value = self.get("min")
            max_value = self.get("max")
            mod = self.get("mod")

            value = float("nan")
            if mod < 0.00001:
                value = random_float(min_value, max_value)
            else:
                n = (max_value - min_value) / mod
                v = random.randint(0, int(n))
                value = min_value + v * mod

            self.set("output", value)

