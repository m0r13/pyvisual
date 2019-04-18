import random
import time
from pyvisual.node.base import Node
from pyvisual.node.op.module import Module
from pyvisual.node import dtype
from pyvisual import util
from glumpy.app import clock
from collections import OrderedDict

def weighted_random(weights):
    s = sum(weights)
    v = random.random() * s
    for i, weight in enumerate(weights):
        v -= weight
        if v < 0:
            return i
    return -1

class TimerEvent(Node):
    class Meta:
        inputs = [
            {"name" : "enabled", "dtype" : dtype.bool, "dtype_args" : {"default" : True}},
            {"name" : "force", "dtype" : dtype.event},
            {"name" : "min", "dtype" : dtype.float, "dtype_args" : {"default" : 1, "range" : [0.00001, float("inf")]}},
            {"name" : "max", "dtype" : dtype.float, "dtype_args" : {"default" : 1, "range" : [0.00001, float("inf")]}},
        ]
        outputs = [
            {"name" : "out", "dtype" : dtype.event},
        ]

    def __init__(self):
        super().__init__(always_evaluate=True)

        self._next_event = None

    def _evaluate(self):
        t = util.time.global_time.time()
        if (self.get("enabled") and self._next_event is not None and t > self._next_event) \
                or self.get("force"):
            self._next_event = None
            self.set("out", True)
        else:
            self.set("out", False)

        if not self.get("enabled"):
            self._next_event = None
        if self._next_event is None:
            min_interval = self.get("min")
            max_interval = self.get("max")
            alpha = random.random()
            self._next_event = t + min_interval * (1.0-alpha) + max_interval * alpha

class FPSTimerEvent(Node):
    class Meta:
        inputs = [
            {"name" : "enabled", "dtype" : dtype.bool, "dtype_args" : {"default" : True}},
            {"name" : "force", "dtype" : dtype.event},
            {"name" : "fps_fraction", "dtype" : dtype.float, "dtype_args" : {"default" : 10.0, "range" : [0.0001, float("inf")]}},
        ]
        outputs = [
            {"name" : "out", "dtype" : dtype.event},
        ]

    def __init__(self):
        super().__init__(always_evaluate=True)

        self._next_event = None
        # have a better way of getting fps
        self._fps = None

    def _evaluate(self):
        t = util.time.global_time.time()
        if (self.get("enabled") and self._next_event is not None and t > self._next_event) \
                or self.get("force"):
            self._next_event = None
            self.set("out", True)
        else:
            self.set("out", False)

        if not self.get("enabled"):
            self._next_event = None
        if self._next_event is None:
            if self._fps is None:
                self._fps = clock.get_default().get_fps_limit()
            f = self.get("fps_fraction")
            if f <= 0.0:
                f = 1.0
            self._next_event = t + 1.0 / (self._fps * f)

class EveryNEvent(Node):
    class Meta:
        inputs = [
            {"name" : "event", "dtype" : dtype.event},
            {"name" : "every_n", "dtype" : dtype.int, "dtype_args" : {"default" : 1, "range" : [1, float("inf")]}},
            {"name" : "offset", "dtype" : dtype.int, "dtype_args" : {"default" : 0}},
            {"name" : "p", "dtype" : dtype.float, "dtype_args" : {"default" : 1, "range" : [0.0, 1.0]}},
        ]
        outputs = [
            {"name" : "out", "dtype" : dtype.event}
        ]

    def __init__(self):
        super().__init__(always_evaluate=True)

        self._counter = None

    def _evaluate(self):
        if self._counter is None:
            self._counter = self.get("offset")
        if self.get("event"):
            self._counter += 1
            if self._counter >= self.get("every_n"):
                self.set("out", random.random() <= self.get("p"))
                self._counter = 0
            else:
                self.set("out", False)
        else:
            self.set("out", False)

class ChooseEvent(Node):
    class Meta:
        inputs = [
            {"name" : "count", "dtype" : dtype.int, "dtype_args" : {"default" : 2, "range" : [0, float("inf")]}},
            {"name" : "event", "dtype" : dtype.event},
        ]
        outputs = [
            {"name" : "dummy0", "dtype" : dtype.int, "dummy" : True},
            {"name" : "dummy1", "dtype" : dtype.int, "dummy" : True},
        ]

    def __init__(self):
        super().__init__(always_evaluate=True)

        # whether to unset all events in the next frame
        # made so event values are not set every frame (which might override force button widget events)
        self._unset_events = True

    def _update_custom_ports(self):
        custom_inputs = []
        custom_outputs = []
        for i in range(int(self.get("count"))):
            input_port = {"name" : "w%d" % i, "dtype" : dtype.float, "dtype_args": {"default" : 1.0, "range" : [0, float("inf")]}}
            output_port = {"name" : "o%d" % i, "dtype" : dtype.event}
            custom_inputs.append(input_port)
            custom_outputs.append(output_port)
        self.set_custom_inputs(custom_inputs)
        self.set_custom_outputs(custom_outputs)

    def _evaluate(self):
        if self.have_inputs_changed("count"):
            self._update_custom_ports()

        if self.get("event"):
            iterator = zip(self.yield_custom_input_values(), self.yield_custom_output_values())
            weights = []
            outputs = []
            for (_0, weight), (_1, output) in iterator:
                weights.append(weight.value)
                outputs.append(output)
            index = weighted_random(weights)
            for i, output in enumerate(outputs):
                output.value = index == i
            # unset all these events in the next frame again
            self._unset_events = True
        elif self._unset_events:
            for _, output in self.yield_custom_output_values():
                output.value = False
            self._unset_events = False

class EventSequencer(Node):
    class Meta:
        inputs = [
            {"name" : "next", "dtype" : dtype.event},
            {"name" : "reset_next", "dtype" : dtype.event},
            {"name" : "modulo", "dtype" : dtype.int, "dtype_args" : {"default" : 32, "range": [1, float("inf")]}},
        ]
        outputs = [
            {"name" : "index", "dtype" : dtype.int},
            {"name" : "next", "dtype" : dtype.event},
            {"name" : "reset", "dtype" : dtype.event},
        ]

    def __init__(self):
        super().__init__()

        self._next_index = 0
        self._next_is_reset = False

    def _evaluate(self):
        if self.get("reset_next"):
            self._next_index = 0
            self._next_is_reset = True

        if self.get("next"):
            index = self._next_index
            modulo = int(self.get("modulo"))
            if modulo < 1:
                modulo = 0
            self.set("index", index)
            self.set("next", True)
            self.set("reset", self._next_is_reset)
            
            self._next_index = (index + 1) % int(self.get("modulo"))
            self._next_is_reset = False

        else:
            self.set("next", False)
            self.set("reset", False)

class EveryNSequencer(Node):
    class Meta:
        inputs = [
            {"name" : "index", "dtype" : dtype.int},
            {"name" : "next", "dtype" : dtype.event},
            {"name" : "reset", "dtype" : dtype.event},
            {"name" : "n", "dtype" : dtype.int, "dtype_args" : {"default" : 1, "range" : [1, float("inf")]}},
            {"name" : "offset", "dtype" : dtype.int, "dtype_args" : {"default" : 0}},
            {"name" : "p", "dtype" : dtype.float, "dtype_args" : {"default" : 1, "range" : [0.0, 1.0]}},
            {"name" : "reset_p", "dtype" : dtype.float, "dtype_args" : {"default" : 1, "range" : [0.0, 1.0]}},
        ]
        outputs = [
            {"name" : "out", "dtype" : dtype.event},
        ]

    def __init__(self):
        super().__init__()

    def _evaluate(self):
        if self.get("next"):
            index = self.get("index")
            n = self.get("n")
            offset = self.get("offset")

            p = self.get("p")
            if self.get("reset"):
                p = self.get("reset_p")
            triggered = (index - offset) % n == 0 and random.random() <= p
            self.set("out", triggered)
        else:
            self.set("out", False)

class EveryNBeat(Module):
    class Meta:
        pass

    def __init__(self):
        super().__init__("EveryNBeat.json", embed_graph=True)
