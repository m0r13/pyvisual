import math
import os
import numpy as np
import imgui
from collections import OrderedDict
from pyvisual.node.base import Node, prepare_port_spec
from pyvisual.node import dtype
from pyvisual.editor import widget
from pyvisual.editor.graph import NodeGraph
from pyvisual.node.io.module import ModuleInput, ModuleOutput
from pyvisual import assets
from collections import defaultdict

class Module(Node):
    class Meta:
        options = {
            "virtual" : True
        }

    def __init__(self, path):
        super().__init__(always_evaluate=True)

        self._inputs = {}
        self._outputs = {}

        self._graph = NodeGraph()
        self._graph.load_file(os.path.join(assets.ASSET_PATH, "saves", "module", path))

        inputs, outputs = [], []
        for node in self._graph.instances:
            if not isinstance(node, (ModuleInput, ModuleOutput)):
                continue

            print(node.name, node.is_input)
            if node.is_input:
                self._inputs[node.name] = node
                inputs.append(node.port_spec)
            else:
                self._outputs[node.name] = node
                outputs.append(node.port_spec)
            node.use_defaults = False

        self.set_custom_inputs(inputs)
        self.set_custom_outputs(outputs)

    def _evaluate(self):
        for name, node in self._inputs.items():
            self.get_input(name).copy_to(node.get_output("value"))

        self._graph.evaluate(reset_instances=False)

        for name, node in self._outputs.items():
            node.get_input("value").copy_to(self.get_output(name))

        self._graph.reset_instances()

    def stop(self):
        self._graph.stop()

