import itertools
import math
import os
from collections import OrderedDict, defaultdict

import numpy as np

import imgui
from pyvisual import assets
from pyvisual.editor import widget
from pyvisual.editor.graph import NodeGraph, NodeGraphListener
from pyvisual.node import dtype
from pyvisual.node.base import Node, prepare_port_spec
from pyvisual.node.io.module import ModuleInput, ModuleOutput

class ModuleInputOutputChanged(NodeGraphListener):
    def __init__(self, callback):
        self.callback = callback
        self.node_filter = lambda node: isinstance(node, (ModuleInput, ModuleOutput))

    def created_node(self, graph, node, ui_data):
        if self.node_filter(node):
            self.callback()

    def removed_node(self, graph, node):
        if self.node_filter(node):
            self.callback()

class Module(Node):

    HAS_SUBGRAPH = True

    class Meta:
        inputs = [
            {"name" : "module_enabled", "dtype" : dtype.bool, "dtype_args" : {"default" : True}},
            {"name" : "module_name", "dtype" : dtype.str, "group" : "additional"},
        ]
        outputs = [
            {"name" : "dummy", "dtype" : dtype.float, "dummy" : True}
        ]
        # put some dummy value here to signalize that it has a state
        initial_state = {
            "dummy" : 0.0
        }
        options = {
            "virtual" : True
        }

    def __init__(self, embed_graph=False):
        # define graph already here as it is used in set_extra of UserModule subclass
        self._graph = None

        super().__init__(always_evaluate=True)

        # whether to set the root graph as the parent graph
        #   (root graph contains beat detection and session as subgraphs,
        #    enables to access beat detection and reference texture variables)
        # this is quite hacky, but allows grabbing beat detection variables
        # on the other side you shouldn't set variables with this option enabled
        self._embed_graph = embed_graph

        # input/output mapping
        # as dictionaries: (i/o name, dtype) => node
        self._inputs = {}
        self._outputs = {}

        # whether module was disabled last evaluated
        # need to force-update all inputs upon next evaluation
        self._was_disabled = False

    @property
    def node_title(self):
        title = self.get("module_name")
        if title.strip() == "":
            return super().node_title
        return "c" + title

    @property
    def subgraph(self):
        return self._graph

    def _init_graph(self, graph):
        # called once graph is constructed, can be overwritten
        pass

    def _update_custom_ports(self):
        self._inputs = {}
        self._outputs = {}

        inputs, outputs = [], []
        for node in self._graph.instances:
            if not isinstance(node, (ModuleInput, ModuleOutput)):
                continue

            # remember i/o node name and dtype to check on each evaluation if that has changed
            if node.is_input:
                self._inputs[(node.name, node.dtype)] = node
                inputs.append((node.order, node.port_spec))
            else:
                self._outputs[(node.name, node.dtype)] = node
                outputs.append((node.order, node.port_spec))
            # important: tell i/o node that it is used in subgraph now
            #   and that values are set from outside
            node.is_in_subgraph = True

        # sort and remove order index
        input_ports = [ t[1] for t in sorted(inputs, key = lambda t: t[0]) ]
        output_ports = [ t[1] for t in sorted(outputs, key = lambda t: t[0]) ]
        self.set_custom_inputs(input_ports)
        self.set_custom_outputs(output_ports)

    def start(self, graph):
        parent = None
        if self._embed_graph:
            parent = graph.parent
        self._graph = NodeGraph(parent=parent)
        self._graph.add_listener(ModuleInputOutputChanged(self._update_custom_ports))
        self._init_graph(self._graph)
        # custom ports are now updated by listener, no more manual _update_custom_ports necessary

    def _evaluate(self):
        if self._graph is None or not self.get("module_enabled"):
            self._was_disabled = True
            return

        # check if any i/o node's name/dtype has changed
        #   which would require us to update our custom ports
        for (name, dt), node in itertools.chain(self._inputs.items(), self._outputs.items()):
            if node.name != name or node.dtype != dt:
                self._update_custom_ports()
                break

        # copy input values from the module node to the i/o nodes in the subgraph
        for (name, dt), node in self._inputs.items():
            input_value = self.get_input(name)
            output_value = node.get_output("value")
            if self._was_disabled:
                # force value updates if module was disabled (we've missed updates probably)
                output_value.value = input_value.value
            else:
                # just copy value over if it has changed
                input_value.copy_to(output_value)
        self._was_disabled = False

        # evaluate graph
        # don't reset instances yet as we want to inspect which outputs have changed
        self._graph.evaluate(reset_instances=False)

        # now copy output values from the i/o nodes in the subgraph back to the module node
        for (name, dt), node in self._outputs.items():
            node.get_input("value").copy_to(self.get_output(name))

        self._graph.reset_instances()

    def stop(self):
        self._graph.stop()

    def reset_state(self, force=False):
        if self.allow_state_randomization and self._graph is not None:
            self._graph.apply_instances(lambda node: node.reset_state(force=force))

    def randomize_state(self, force=False):
        if self.allow_state_randomization and self._graph is not None:
            self._graph.apply_instances(lambda node: node.randomize_state(force=force))

class StaticModule(Module):
    def __init__(self, path, embed_graph=False):
        super().__init__(embed_graph=embed_graph)

        self._path = path

    def _init_graph(self, graph):
        graph.load_file(os.path.join(assets.ASSET_PATH, "saves", "module", self._path))

class UserModule(Module):

    # Let's just assume that user modules use OpenGL
    USES_OPENGL = True

    class Meta:
        options = {
            "virtual" : False
        }

    def get_extra(self):
        extra = super().get_extra()
        extra["subgraph"] = self._graph.serialize(as_json_dict=True)
        return extra

    def set_extra(self, extra):
        super().set_extra(extra)

        # assumption: when graph is None, it's the initial set_extra in the node constructor
        #   there is no subgraph data yet, so just ignore it
        if self._graph is not None:
            self._graph.clear()
            self._graph.unserialize(extra.get("subgraph", {}))

