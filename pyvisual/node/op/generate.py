import time
import math
import random
import noise
import numpy as np
from collections import OrderedDict
from pyvisual.node.base import Node
from pyvisual.node import dtype
from pyvisual.editor import widget
from pyvisual import util, assets
import imgui

def random_time(node, a=-10000.0, b=10000.0):
    alpha = random.random()
    return (1.0-alpha)*a + alpha*b

LFO_OSCILLATORS = OrderedDict(
    square=lambda t, length, phase: float(math.fmod(t - phase, length) < 0.5 * length),
    saw=lambda t, length, phase: float(2.0 / math.pi * math.atan(math.tan((2*math.pi*t + phase - math.pi * 0.5) / length))) * 0.5 + 0.5,
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
        if length == 0.0:
            length = 0.000001
        self._time = self._timer(1.0 / length, False)
        value = LFO.OSCILLATORS[generator](self._time, 1.0, self.get("phase"))
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
            {"name" : "f", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0, "range" : [0.000001, float("inf")]}},
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
        f = self.get("f") * 2.0
        if f == 0.0:
            self.set("output", self.get("min"))
        self._time = self._timer(f, False)
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
            {"name" : "enabled", "dtype" : dtype.bool, "dtype_args" : {"default" : True}},
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
        if not self.get("enabled") and not self.get("reset"):
            self._timer(0.0, False)
            return

        self._time = self._timer(self.get("factor"), self.get("reset"))
        if self.get("reset"):
            self._time = 0.0

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

class MoveAndJump(Node):
    class Meta:
        inputs = [
            {"name" : "event", "dtype" : dtype.event},
            {"name" : "global_speed", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "speed0", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "speed1", "dtype" : dtype.float, "dtype_args" : {"default" : -1.0}},
            {"name" : "jump_amount", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "jump_smooth", "dtype" : dtype.bool, "dtype_args" : {"default" : False}},
            {"name" : "jump_type", "dtype" : dtype.int, "dtype_args" : {"choices" : ["fixed", "relative_speed", "relative_duration"]}},
            {"name" : "timer_type", "dtype" : dtype.int, "dtype_args" : {"choices" : ["identity", "saw", "triangle", "sine"]}},
            {"name" : "timer_min", "dtype": dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "timer_max", "dtype": dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "timer_duration", "dtype": dtype.float, "dtype_args" : {"default" : 1.0, "range" : [0.0, float("infinity")]}},
        ]
        outputs = [
            {"name" : "speed", "dtype" : dtype.float},
            {"name" : "jump", "dtype" : dtype.event},
            {"name" : "jump_amount", "dtype" : dtype.float},
            {"name" : "value", "dtype" : dtype.float},
            {"name" : "value_no_jumps", "dtype" : dtype.float},
        ]
        initial_state = {
            "dir" : 0,
            "time" : 0.0,
        }
        random_state = {
            "dir" : lambda node: random.randint(0, 1),
            "time" : random_time,
        }

    def __init__(self):
        self._dir = 0
        self._timer = util.time.ScalableTimer()
        self._time_offset = 0.0
        self._time = 0.0

        self._lfo = None

        super().__init__(always_evaluate=True)

    def _emit_value(self, name, t):
        if self._lfo is None:
            self.set(name, t)
            return

        timer_min = self.get("timer_min")
        timer_max = self.get("timer_max")
        timer_duration = self.get("timer_duration")

        value = self._lfo(t, timer_duration, 0.0)
        value = timer_min + value * (timer_max - timer_min)
        self.set(name, value)

    def _evaluate(self):
        global_speed = self.get("global_speed")
        timer_duration = self.get("timer_duration")

        event = self.get("event")
        if event:
            self._dir = (self._dir + 1) % 2

        speed = self.get("speed1") if self._dir else self.get("speed0")
        self.set("speed", global_speed * speed)
        if event:
            jump_type = self.get("jump_type")

            jump_factor = 1.0
            if jump_type == 1:
                jump_factor = speed
            elif jump_type == 2:
                jump_factor = timer_duration
            amount = self.get("jump_amount") * jump_factor
            self._time_offset += amount
            self.set("jump", True)
            self.set("jump_amount", amount)
        else:
            self.set("jump", False)

        self._time = self._timer(global_speed * speed)

        timer_type = self.get_input("timer_type") 
        if timer_type.has_changed():
            index = int(self.get("timer_type"))
            if index == 0:
                self._lfo = None
            else:
                lfos = list(LFO_OSCILLATORS.values())
                self._lfo = lfos[min(len(lfos) - 1, index)]

        self._emit_value("value", self._time + self._time_offset)
        self._emit_value("value_no_jumps", self._time)

    def get_state(self):
        return {"dir" : self._dir, "time" : self._time, "time_offset" : self._time_offset}

    def set_state(self, state):
        if "dir" in state:
            self._dir = state["dir"]
        if "time" in state:
            self._timer = util.time.ScalableTimer(state["time"])
        if "time_offset" in state:
            self._time_offset = state["time_offset"]

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
            {"name" : "clamp_min", "dtype" : dtype.float, "dtype_args" : {"default" : float("-inf")}, "group" : "additional"},
            {"name" : "clamp_max", "dtype" : dtype.float, "dtype_args" : {"default" : float("inf")}, "group" : "additional"},
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
        value = min(self.get("clamp_max"), max(self.get("clamp_min"), value))
        return value

    def get_state(self):
        return {"value" : self.get_output("output").value}

    def set_state(self, state):
        if "value" in state:
            self.set("output", state["value"])

class RandomBool(Node):
    class Meta:
        inputs = [
            {"name" : "generate", "dtype" : dtype.event},
            {"name" : "p", "dtype" : dtype.float, "dtype_args" : {"default" : 0.5, "range" : [0.0, 1.0]}},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.bool}
        ]
        initial_state = {
            "value" : lambda node: random.random() > 0.5
        }
        random_state = {
            "value" : lambda node: node.generate_bool()
        }

    def _evaluate(self):
        if self.get("generate"):
            self.randomize_state()

    def generate_bool(self):
        return random.random() < self.get("p")

    def get_state(self):
        return {"value" : self.get_output("output").value}

    def set_state(self, state):
        if "value" in state:
            self.set("output", state["value"])

class ChooseFile(Node):
    class Meta:
        inputs = [
            {"name" : "wildcard", "dtype" : dtype.assetpath},
            {"name" : "next", "dtype" : dtype.event},
            {"name" : "randomize", "dtype" : dtype.event},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.str},
        ]
        initial_state = {
            "index" : lambda node: 0
        }
        random_state = {
            "index" : lambda node: node.generate_index(shuffle=True)
        }

    def __init__(self):
        self._files = None
        self._index = 0

        super().__init__()

    def generate_index(self, shuffle=True):
        count = len(self._files)
        if count == 0 or count == 1:
            return 0
        if shuffle:
            return (self._index + random.randint(1, count - 1)) % count
        else:
            return (self._index + 1) % count

    def _evaluate(self):
        if self.have_inputs_changed("wildcard") or self._last_evaluated == 0.0:
            wildcard = self.get("wildcard").strip()
            if not wildcard:
                self._files = []
            else:
                self._files = sorted(assets.glob_paths(self.get("wildcard")))
            self.set_state({"index" : 0})

        if self.get("next"):
            self.set_state({"index" : self.generate_index(shuffle=False)})
        if self.get("randomize"):
            self.randomize_state()

    def _show_custom_ui(self):
        super()._show_custom_ui()

        if imgui.button("choose file"):
            imgui.open_popup("choose_file")
        if imgui.begin_popup("choose_file"):
            for i, path in enumerate(self._files):
                if imgui.menu_item(path, "", False, True)[0]:
                    self.set_state({"index" : i})
            imgui.end_popup()

    def get_state(self):
        return {"index" : self._index}

    def set_state(self, state):
        if "index" in state:
            self._index = state["index"]
            if self._files is None:
                return
            if self._index < len(self._files):
                self.set("output", self._files[self._index])
            else:
                self.set("output", "")

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
            {"name" : "per_hour", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.event},
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(always_evaluate=True, *args, **kwargs)

        self._next = 0

    def _evaluate(self):
        t = util.time.global_time.time()

        per_minute = self.get("per_minute") + self.get("per_hour") / 60.0
        if per_minute == 0.0:
            per_minute = 1.0
        enabled = self.get("enabled") and per_minute != 0.0
        if self._next < t and self.get("enabled"):
            self._next = t + random.expovariate(1.0 / (60.0 / per_minute))
            self.set("output", True)
        else:
            self.set("output", False)

    def _show_custom_context(self):
        imgui.text("Next event: %ds" % (self._next - util.time.global_time.time()))
        if imgui.button("force"):
            self._next = 0.0

