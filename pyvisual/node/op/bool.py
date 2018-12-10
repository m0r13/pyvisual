import random
import numpy as np
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

class ChooseBool(Node):
    class Meta:
        inputs = [
            {"name" : "count", "dtype" : dtype.int, "dtype_args" : {"default" : 2, "range" : [0, float("inf")]}},
            {"name" : "event", "dtype" : dtype.event},
            {"name" : "min", "dtype" : dtype.int, "dtype_args" : {"default" : 1, "range" : [0, float("inf")]}},
            {"name" : "max", "dtype" : dtype.int, "dtype_args" : {"default" : 1, "range" : [0, float("inf")]}},
        ]
        outputs = [
            {"name" : "dummy0", "dtype" : dtype.int, "dummy" : True},
            {"name" : "dummy1", "dtype" : dtype.int, "dummy" : True},
            {"name" : "dummy2", "dtype" : dtype.int, "dummy" : True},
            {"name" : "dummy3", "dtype" : dtype.int, "dummy" : True},
        ]

    def _update_custom_ports(self):
        custom_inputs = []
        custom_outputs = []
        for i in range(int(self.get("count"))):
            input_port = {"name" : "w%d" % i, "dtype" : dtype.float, "dtype_args": {"default" : 1.0, "range" : [0, float("inf")]}}
            output_port = {"name" : "o%d" % i, "dtype" : dtype.bool}
            custom_inputs.append(input_port)
            custom_outputs.append(output_port)
        self.set_custom_inputs(custom_inputs)
        self.set_custom_outputs(custom_outputs)

    def _evaluate(self):
        if self.have_inputs_changed("count"):
            self._update_custom_ports()

        if self.get("min") > self.get("count"):
            self.get_input("min").value = self.get("count")
        if self.get("max") > self.get("count"):
            self.get_input("max").value = self.get("count")
        if self.get("min") > self.get("max"):
            self.get_input("max").value = self.get("min")

        if self.get("event"):
            count = self.get("count")
            min_enabled = max(0, self.get("min"))
            max_enabled = max(min_enabled, min(count, self.get("max")))
            enable_count = random.randint(min_enabled, max_enabled)

            weights = np.zeros((count,))
            for i, (_, weight) in enumerate(self.yield_custom_input_values()):
                weights[i] = weight.value
            weights = weights / np.sum(weights)

            enabled = [False]*count
            choices = random.choices(list(range(count)), weights=weights, k=enable_count)
            choices = np.random.choice(count, enable_count, replace=False, p=weights)
            for i in choices:
                enabled[i] = True

            for i, (_, output) in enumerate(self.yield_custom_output_values()):
                output.value = enabled[i]

# TODO maybe also allow other time distributions
class RandomBool(Node):
    class Meta:
        inputs = [
            {"name" : "on_min", "dtype" : dtype.float, "dtype_args" : {"default" : 0.1}},
            {"name" : "on_max", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "on_scale", "dtype" : dtype.float, "dtype_args" : {"default" : 0.5}},
            {"name" : "off_min", "dtype" : dtype.float, "dtype_args" : {"default" : 0.1}},
            {"name" : "off_max", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "off_scale", "dtype" : dtype.float, "dtype_args" : {"default" : 0.5}},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float}
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(always_evaluate=True, *args, **kwargs)

        self._status = 0.0
        self._next_switch = 0

    def _evaluate(self):
        t = time.time()

        old_status = self._status
        if self._next_switch < t:
            def sample_time(a, b, scale):
                if scale < 10e-6:
                    return np.random.uniform(low=a, high=b)
                else:
                    alpha = np.random.exponential(scale=scale)
                    return (1.0 - alpha) * a + alpha * b
            if not self._status:
                self._next_switch = t + sample_time(self.get("on_min"), self.get("on_max"), self.get("on_scale"))
            else:
                self._next_switch = t + sample_time(self.get("off_min"), self.get("off_max"), self.get("off_scale"))
            self._status = 1.0 - self._status

        self.set("output", float(self._status))

