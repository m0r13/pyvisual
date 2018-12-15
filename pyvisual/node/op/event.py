import random
import time
from pyvisual.node.base import Node
from pyvisual.node import dtype
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
        t = time.time()
        if self.get("enabled") and self._next_event is not None and t > self._next_event:
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

class EveryNEvent(Node):
    class Meta:
        inputs = [
            {"name" : "event", "dtype" : dtype.event},
            {"name" : "every_n", "dtype" : dtype.int, "dtype_args" : {"default" : 1, "range" : [1, float("inf")]}},
            {"name" : "p", "dtype" : dtype.float, "dtype_args" : {"default" : 1, "range" : [0.0, 1.0]}},
        ]
        outputs = [
            {"name" : "out", "dtype" : dtype.event}
        ]

    def __init__(self):
        super().__init__(always_evaluate=True)

        self._counter = 0

    def _evaluate(self):
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
        else:
            for _, output in self.yield_custom_output_values():
                output.value = False

