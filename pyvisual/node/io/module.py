import math
from collections import OrderedDict
from collections import defaultdict

import numpy as np

import imgui
from pyvisual.editor import widget
from pyvisual.node import dtype
from pyvisual.node.base import Node, prepare_port_spec

DTYPE_NAMES = list(dtype.dtypes.keys())
DTYPES = list(dtype.dtypes.values())
assert "float" in  DTYPE_NAMES
DTYPES_DEFAULT = DTYPE_NAMES.index("float")

class ModuleInputOutput(Node):
    class Meta:
        inputs = [
            {"name" : "name", "dtype" : dtype.str},
            {"name" : "dtype", "dtype" : dtype.int, "dtype_args" : {"choices" : DTYPE_NAMES, "default" : DTYPES_DEFAULT}},
            {"name" : "order", "dtype" : dtype.int, "group" : "additional"},
        ]
        outputs = [
        ]
        options = {
            "virtual" : True
        }

    def __init__(self, is_input):
        super().__init__()

        self.is_input = is_input
        # whether this i/o node is actually in use in a subgraph
        # if yes: value is set from outside
        # if no: use/provide test value that is a separate port
        self.is_in_subgraph = False

        self.value_name = "value"
        self.default_value_name = "default_value"
        self.test_value_name = "test_value"
        if not self.is_input:
            self.value_name, self.test_value_name = self.test_value_name, self.value_name

        # initialize custom ports with default values
        self._update_custom_ports()

    @property
    def name(self):
        return self.get("name")

    @property
    def dtype(self):
        dt = int(self.get("dtype"))
        dt = max(0, min(len(DTYPES), dt))
        return DTYPES[dt]

    @property
    def order(self):
        return self.get("order")

    @property
    def port_spec(self):
        port_spec = {"name" : self.name, "dtype" : self.dtype}
        if self.is_input:
            port_spec["dtype_args"] = {"default" : self.get(self.default_value_name)}
        return port_spec

    def _update_custom_ports(self):
        custom_inputs = []
        custom_outputs = []

        dt = dtype.float
        # make sure that we don't change the dtype value if it wasn't created yet!!
        # that's an ugly hack, but okay
        if "i_dtype" in self.values:
            dt = self.dtype
        if self.is_input:
            custom_inputs.append({"name" : self.default_value_name, "dtype" : dt})
        custom_inputs.append({"name" : self.test_value_name, "dtype" : dt})
        custom_outputs.append({"name" : self.value_name, "dtype" : dt})

        self.set_custom_inputs(custom_inputs)
        self.set_custom_outputs(custom_outputs)

    def _evaluate(self):
        if self.have_inputs_changed("name", "dtype"):
            self._update_custom_ports()

        if not self.is_in_subgraph:
            self.get_input(self.test_value_name).copy_to(self.get_output(self.value_name))

class ModuleInput(ModuleInputOutput):
    class Meta:
        pass

    def __init__(self):
        super().__init__(is_input=True)

class ModuleOutput(ModuleInputOutput):
    class Meta:
        pass

    def __init__(self):
        super().__init__(is_input=False)

