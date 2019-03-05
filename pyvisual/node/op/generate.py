import time
import math
import random
import noise
import numpy as np
from collections import OrderedDict
from pyvisual.node.base import Node
from pyvisual.node import dtype
from pyvisual.editor import widget
from pyvisual import util

def random_time(node, a=-10000.0, b=10000.0):
    alpha = random.random()
    return (1.0-alpha)*a + alpha*b

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
            {"name" : "type", "dtype" : dtype.int, "dtype_args" : {"default" : 2, "choices" : list(LFO_OSCILLATORS.keys())}},
            {"name" : "length", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0, "range" : [0.000001, float("inf")]}},
            {"name" : "phase", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "min", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "max", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float}
        ]
        initial_state = {
            "time" : 0.0
        }
        random_state = {
            "time" : random_time
        }
        options = {
            "category" : "generate",
            "show_title" : True
        }

    def __init__(self):
        super().__init__(always_evaluate=True)

        self._time = 0.0

    def _evaluate(self):
        generator = int(self.get("type"))
        length = self.get("length")
        self._time = self._timer(1.0 / length, False)
        value = LFO.OSCILLATORS[generator](self._time, 1.0 + 0.0 * self.get("length"), self.get("phase"))
        value = self.get("min") + value * (self.get("max") - self.get("min"))
        self.set("output", value)

    def get_state(self):
        return {"time" : self._time}

    def set_state(self, state):
        if "time" in state:
            self._timer = util.time.ScalableTimer(state["time"])

class PWM(Node):
    class Meta:
        inputs = [
            {"name" : "length", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0, "range" : [0.000001, float("inf")]}},
            {"name" : "value", "dtype" : dtype.float, "dtype_args" : {"default" : 0.5, "range" : [0.0, 1.0]}},
            {"name" : "min", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "max", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
        ]
        initial_state = {
            "time" : 0.0
        }
        random_state = {
            "time" : random_time
        }
        outputs = [
            {"name" : "output", "dtype" : dtype.float}
        ]

    def __init__(self):
        super().__init__(always_evaluate=True)

        self._time = 0.0

    def _evaluate(self):
        length = self.get("length")
        if length == 0:
            self.set("output", float("nan"))
            return
        self._time = self._timer(1.0 / length, False)
        if self._time % 1.0 < self.get("value"):
            self.set("output", self.get("max"))
        else:
            self.set("output", self.get("min"))

    def get_state(self):
        return {"time" : self._time}

    def set_state(self, state):
        if "time" in state:
            self._timer = util.time.ScalableTimer(state["time"])

class Time(Node):
    class Meta:
        inputs = [
            {"name" : "factor", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "mod", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}, "group" : "additional"},
            {"name" : "reset", "dtype" : dtype.event}
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float}
        ]
        initial_state = {
            "time" : 0.0
        }
        random_state = {
            "time" : random_time
        }
        options = {
            "category" : "generate",
            "show_title" : True
        }

    def __init__(self):
        super().__init__(always_evaluate=True)

        self._time = 0.0

    def _evaluate(self):
        self._time = self._timer(self.get("factor"), self.get("reset"))

        mod = self.get("mod")
        if mod > 0.00001:
            # round time to mod
            value = self._time - (self._time % mod)
            self.set("output", value)
        else:
            self.set("output", self._time)

    def get_state(self):
        return {"time" : self._time}

    def set_state(self, state):
        if "time" in state:
            self._timer = util.time.ScalableTimer(state["time"])

def random_float(a, b):
    alpha = random.random()
    value = a * (1.0-alpha) + b * alpha
    return value

def state_initial_float(node):
    if "i_min" in node.values:
        return node.get("min")
    return 0.0

def state_random_float(node):
    return node.generate_float()

class RandomFloat(Node):
    class Meta:
        inputs = [
            {"name" : "generate", "dtype" : dtype.event},
            {"name" : "min", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "max", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "mod", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float}
        ]
        initial_state = {
            "value" : state_initial_float
        }
        random_state = {
            "value" : state_random_float
        }
        options = {
            "category" : "generate",
            "show_title" : True
        }

    def _evaluate(self):
        if self.get("generate"):
            self.randomize_state()

    def generate_float(self):
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
        return value

    def get_state(self):
        return {"value" : self.get_output("output").value}

    def set_state(self, state):
        if "value" in state:
            self.set("output", state["value"])

class Noise1D(Node):
    class Meta:
        inputs = [
            {"name" : "x", "dtype" : dtype.float},
            {"name" : "min", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "max", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "octaves", "dtype" : dtype.int, "dtype_args" : {"default" : 1}, "group" : "additional"},
            {"name" : "persistence", "dtype" : dtype.float, "dtype_args" : {"default" : 0.5}, "group" : "additional"},
            {"name" : "lacunarity", "dtype" : dtype.float, "dtype_args" : {"default" : 2.0}, "group" : "additional"},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float}
        ]

    def _evaluate(self):
        octaves = int(self.get("octaves"))
        persistence = self.get("persistence")
        lacunarity = self.get("lacunarity")
        alpha = noise.pnoise1(self.get("x"), octaves=octaves, persistence=persistence, lacunarity=lacunarity) * 0.5 + 0.5
        self.set("output", (1.0 - alpha) * self.get("min") + alpha * self.get("max"))

class PoissonTimer(Node):
    class Meta:
        inputs = [
            {"name" : "enabled", "dtype" : dtype.bool, "dtype_args" : {"default" : True}},
            {"name" : "per_minute", "dtype" : dtype.float, "dtype_args" : {"default" : 6.0}},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.event},
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(always_evaluate=True, *args, **kwargs)

        self._next = 0

    def _evaluate(self):
        t = util.time.global_time.time()

        if self._next < t and self.get("enabled"):
            per_minute = self.get("per_minute")
            if per_minute == 0.0:
                pass
            self._next = t + random.expovariate(1.0 / (60.0 / self.get("per_minute")))
            self.set("output", True)
        else:
            self.set("output", False)

