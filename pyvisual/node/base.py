import clipboard
import copy
import imgui
import json
import time
import random
from collections import OrderedDict

def find_node_base(bases):
    bases = list(filter(lambda b: issubclass(b, Node), bases))
    assert len(bases) == 1, "There must be exactly one Node base class"
    return bases[0]

class NodeMeta(type):
    node_types = []

    def __new__(meta, name, bases, dct):
        base = None
        if name == "Node":
            base = None
        else:
            base = find_node_base(bases)
        dct["base_node"] = base
        cls = super().__new__(meta, name, bases, dct)
        cls.spec = NodeSpec.from_cls(cls)
        meta.node_types.append(cls)
        #print("Registered node type: %s" % cls)
        return cls

def port_id(port_spec, is_input):
    prefix = "i_" if is_input else "o_"
    return prefix + port_spec["name"]

def port_name(port_id):
    assert port_id[:2] in ("i_", "o_")
    return port_id[2:]

def is_input(port_id):
    assert port_id[:2] in ("i_", "o_")
    return port_id[:2] == "i_"

def prepare_port_spec(port_spec, is_input):
    assert "name" in port_spec
    assert "dtype" in port_spec
    port_spec.setdefault("dtype_args", {})
    port_spec.setdefault("widgets", [])
    port_spec.setdefault("default", None)
    port_spec.setdefault("hide", False)
    port_spec.setdefault("dummy", False)
    port_spec.setdefault("group", "default")

    if is_input:
        port_spec.setdefault("manual_input", True)
    else:
        port_spec.setdefault("manual_input", False)

# evaluate a set of key -> value pairs
# may be passed as dictionary or callable (argument: node)
# the values in the pairs might be functions too that return the actual value
def evaluate_values(node, values_or_fn):
    # evaluate if passed as function
    values = values_or_fn(node) if callable(values_or_fn) else values_or_fn
    # make a copy to not modify original dictionary
    values = dict(values)
    for key, value in values.items():
        if callable(value):
            values[key] = value(node)
    return values

class NodeTypeNotFound(Exception):
    pass

class NodeSpec:
    def __init__(self, cls=None,
            inputs=None, outputs=None,
            presets=None,
            initial_state=None, random_state=None,
            options={}):
        self.cls = cls
        self.inputs = inputs if inputs is not None else []
        self.outputs = outputs if outputs is not None else []
        self.presets = presets if presets is not None else []
        self.initial_state = initial_state if initial_state is not None else {}
        self.random_state = random_state if random_state is not None else {}
        self.options = dict(options)

    @property
    def module_name(self):
        return self.cls.__module__.replace("pyvisual.node.", "")

    @property
    def name(self):
        return self.cls.__name__

    @property
    def ports(self):
        for port_id, port_spec in self.input_ports:
            yield port_id, port_spec
        for port_id, port_spec in self.output_ports:
            yield port_id, port_spec

    @property
    def input_ports(self):
        for port_spec in self.inputs:
            yield port_id(port_spec, True), copy.deepcopy(port_spec)

    @property
    def output_ports(self):
        for port_spec in self.outputs:
            yield port_id(port_spec, False), copy.deepcopy(port_spec)

    def instantiate_node(self):
        return self.cls()

    def append(self, child_spec):
        self.cls = child_spec.cls
        self.inputs = self.inputs + child_spec.inputs
        self.outputs = self.outputs + child_spec.outputs
        # TODO how should states / presets be inherited ?
        self.presets = child_spec.presets
        self.initial_state = child_spec.initial_state
        self.random_state = child_spec.random_state
        self.options = child_spec.options

    def __repr__(self):
        return "NodeSpec(cls=%s, inputs=%s, outputs=%s, options=%s)" % (self.cls, self.inputs, self.outputs, self.options)

    @staticmethod
    def from_cls(node_cls):
        bases = []
        base_cls = node_cls
        while base_cls is not None:
            bases.insert(0, base_cls)
            base_cls = base_cls.base_node

        def parse(cls):
            inputs = getattr(cls.Meta, "inputs", [])
            outputs = getattr(cls.Meta, "outputs", [])
            presets = getattr(cls.Meta, "presets", [])
            initial_state = getattr(cls.Meta, "initial_state", {})
            random_state = getattr(cls.Meta, "random_state", {})
            options = getattr(cls.Meta, "options", {})
            return NodeSpec(cls=cls,
                    inputs=inputs, outputs=outputs,
                    presets=presets,
                    initial_state=initial_state, random_state=random_state,
                    options=options)

        spec = NodeSpec()
        for cls in bases:
            spec.append(parse(cls))

        # set spec defaults at last
        spec.options.setdefault("virtual", False)
        spec.options.setdefault("category", "")
        spec.options.setdefault("show_title", True)
        for i, port_spec in enumerate(spec.inputs + spec.outputs):
            is_input = i < len(spec.inputs)
            prepare_port_spec(port_spec, is_input)
        return spec

    @staticmethod
    def from_name(node_name):
        for cls in NodeMeta.node_types:
            if cls.__name__ == node_name:
                return NodeSpec.from_cls(cls)
        raise NodeTypeNotFound()

class Node(metaclass=NodeMeta):
    class Meta:
        inputs = []
        outputs = []

    # Forces this node type to be executed as early as possible in the graph.
    # This means possibly even before the nodes where its input values come from.
    # Required for delaying a value by a frame in preventing problems with circular connections.
    # See also: DelayFloat
    FORCE_EARLY_EXECUTION = False

    USES_OPENGL = False

    def __init__(self, always_evaluate=False):
        self.always_evaluate = always_evaluate
        self.graph = None
        self.id = -1
        self.dfs_index = -1
        self._evaluated = False
        self._last_evaluated = 0.0
        self._force_evaluate = False

        self.initial_manual_values = {}
        self.values = {}

        self.input_nodes = set()
        self.base_input_ports = OrderedDict(self.spec.input_ports)
        self.base_output_ports = OrderedDict(self.spec.output_ports)
        self.custom_input_ports = OrderedDict()
        self.custom_output_ports = OrderedDict()
        self.update_ports()

        # set default state/extra information
        self.set_state(evaluate_values(self, self.spec.initial_state))
        self.set_extra({
            "allow_preset_randomization" : False
        })
        # TODO make this persistent?
        # question: also add temporary version of this?
        self.allow_state_randomization = True

    def update_ports(self):
        self.input_ports = OrderedDict()
        self.input_ports.update(self.base_input_ports)
        self.input_ports.update(self.custom_input_ports)
        assert(len(set(self.base_input_ports.keys()).intersection(self.custom_input_ports.keys())) == 0)

        self.output_ports = OrderedDict()
        self.output_ports.update(self.base_output_ports)
        self.output_ports.update(self.custom_output_ports)
        assert(len(set(self.base_output_ports.keys()).intersection(self.custom_output_ports.keys())) == 0)

        self.ports = OrderedDict()
        self.ports.update(self.input_ports)
        self.ports.update(self.output_ports)

        for port_id in list(self.values.keys()):
            if port_id in self.ports:
                continue
            # disconnect/delete value here
            # TODO
            # we just delete the value here for now
            # but a possible connection should be properly removed too
            # (right now the removed value is detected by the ui-node and then the connection is deleted there)
            del self.values[port_id]

    @property
    def custom_ports(self):
        # kinda slow, don't use where performance matters!
        p = OrderedDict()
        p.update(self.custom_input_ports)
        p.update(self.custom_output_ports)
        return p

    def get_port(self, port_id):
        assert port_id in self.ports
        return self.ports[port_id]

    def _prepare_ports(self, port_specs, old_ports, is_input):
        # returns ordered dict with port_id => port_spec

        # TODO stuff around old_ports is hacky
        # removes all input/output ports whose base dtype has changed
        # because we want to remove them only when they have really changed
        # otherwise the value would be lost
        # keeping the values might be intended. maybe it's not after all?

        ports = OrderedDict()
        for port_spec in port_specs:
            prepare_port_spec(port_spec, True)
            port_id = ("i_%s" if is_input else "o_%s") % port_spec["name"]
            if port_id in old_ports:
                old_port_spec = old_ports[port_id]
                if old_port_spec["dtype"].base_type != port_spec["dtype"].base_type:
                    if port_id in self.values:
                        del self.values[port_id]
            ports[port_id] = port_spec
        return ports

    def set_custom_inputs(self, port_specs):
        # TODO see _prepare_ports
        self.custom_input_ports = self._prepare_ports(port_specs, self.custom_input_ports, True)
        self.update_ports()

    def set_custom_outputs(self, port_specs):
        # TODO see _prepare_ports
        self.custom_output_ports = self._prepare_ports(port_specs, self.custom_output_ports, False)
        self.update_ports()

    def yield_custom_input_values(self):
        for port_id in self.custom_input_ports.keys():
            yield port_id, self.get_value(port_id)

    def yield_custom_output_values(self):
        for port_id in self.custom_output_ports.keys():
            yield port_id, self.get_value(port_id)

    def update_input_nodes(self):
        self.input_nodes = set()
        for port_id, value in self.values.items():
            #if is_input(port_id) and value.is_connected:
            if port_id[:2] == "i_" and value.is_connected:
                self.input_nodes.add(value.connected_node)

    def have_any_inputs_changed(self):
        for port_id, value in self.values.items():
            if port_id[:2] == "i_" and value.has_changed_fast():
                return True
        return False

    def have_inputs_changed(self, *port_names):
        assert len(port_names) != 0, "Use have_any_inputs_changed instead"
        for port_name in port_names:
            if self.get_input(port_name).has_changed_fast():
                return True
        return False

    @property
    def evaluated(self):
        return self._evaluated
    @evaluated.setter
    def evaluated(self, evaluated):
        # at the beginning of each run where all nodes are not evaluated yet
        # all values will be set unchanged so changes in evaluating nodes will
        # result in the nodes after them to be evaluated accordingly
        if not evaluated:
            for value in self.values.values():
                value.reset_changed()
        self._evaluated = evaluated

    def reset_evaluated(self):
        for value in self.values.values():
            value.reset_changed()
        self._evaluated = False

    def _create_value(self, port_id):
        assert port_id in self.ports, "Port %s not found" % port_id 
        port_spec = self.ports[port_id]
        is_input = port_id.startswith("i_")

        dtype = port_spec["dtype"]
        dtype_args = port_spec["dtype_args"]
        default_value = dtype_args["default"] if "default" in dtype_args else dtype.default()
        if port_id in self.initial_manual_values:
            default_value = self.initial_manual_values[port_id]
            del self.initial_manual_values[port_id]

        value = None
        if is_input:
            manual_input = SettableValueHolder(default_value)
            value = InputValueHolder(manual_input)
        else:
            value = SettableValueHolder(default_value)
        return value

    def get_input(self, name):
        return self.get_value("".join(["i_", name]))
    def get_output(self, name):
        return self.get_value("".join(["o_", name]))
    def get_value(self, port_id):
        if not port_id in self.values:
            self.values[port_id] = self._create_value(port_id)
        return self.values[port_id]

    def get(self, name):
        return self.get_input(name).value
    def set(self, name, value):
        output = self.get_output(name)
        # cache numeric values
        if isinstance(value, (float, int, bool)):
            if abs(output.value - value) > 10e-6:
                output.value = value
        else:
            output.value = value
    def force_evaluate(self):
        self._force_evaluate = True

    @property
    def descriptive_title(self):
        return None

    def start(self, graph):
        pass

    def evaluate(self):
        # update a node
        # return True if node needed update

        if not self._evaluated and (self.always_evaluate or self._last_evaluated == 0.0 or self._force_evaluate or self.have_any_inputs_changed()):
            self._force_evaluate = False
            self._evaluate()
            self._evaluated = True
            self._last_evaluated = time.time()
            return True
        return False

    def stop(self):
        pass

    def _evaluate(self):
        # to be implemented by child nodes
        # never call from outside! use evaluate() instead
        pass

    def _after_evaluate(self):
        # Called after all nodes have been evaluated, but values (more precise: their has_changed state) haven't been resetted yet!
        # Useful for DelayFloat value.
        pass

    def _show_custom_ui(self):
        # called from ui-node to draw custom imgui node ui
        # called only when that ui would be visible
        pass

    def _show_custom_context(self):
        # called from ui-node to add custom entries in nodes context menu
        # called only when that context menu is visible

        has_state = len(self.spec.initial_state) != 0
        has_presets = len(self.spec.presets) != 0

        if has_state:
            imgui.separator()

            if imgui.button("reset state"):
                self.reset_state(force=True)
            imgui.same_line()
            if imgui.button("randomize state"):
                self.randomize_state(force=True)

            changed, self.allow_state_randomization= imgui.checkbox("allow state randomization", self.allow_state_randomization)

        if has_presets:
            imgui.separator()

            if imgui.button("default preset"):
                self.reset_preset(force=True)
            imgui.same_line()
            if imgui.button("random preset"):
                self.randomize_preset(force=True)
            imgui.same_line()
            if imgui.button("choose preset..."):
                imgui.open_popup("choose_preset")
            if imgui.begin_popup("choose_preset"):
                for name, values in self.spec.presets:
                    if imgui.button(name):
                        self.set_preset(values)
                imgui.end_popup()

            changed, self.allow_preset_randomization = imgui.checkbox("allow preset randomization", self.allow_preset_randomization)

        if imgui.button("copy current as preset"):
            # copy only keys that are contained in (first) preset
            # TODO see how this behavior works
            keys = None if not has_presets else list(self.spec.presets[0][1].keys())
            values = OrderedDict()
            for port_id, value in self.values.items():
                if not is_input(port_id):
                    continue
                name = port_name(port_id)
                if keys is not None and name not in keys:
                    continue
                values[name] = value.value
            preset = ["name", values]
            clipboard.copy(json.dumps(preset))

    # overwrite if necessary
    def get_state(self):
        return {}

    # overwrite if necessary
    # sets state (dict with input name -> value pairs) on node
    # use evaluate_values before passing values here!!
    def set_state(self, state):
        pass

    def set_preset(self, values):
        values = evaluate_values(self, values)
        for key, value in values.items():
            self.get_input(key).value = value

    def reset_preset(self, force=False):
        # TODO how to handle randomization here?
        # --> maybe apply the default value?
        if len(self.spec.presets) == 0:
            return
        if not force and not self.allow_preset_randomization:
            return
        name, values = self.spec.presets[0]
        self.set_preset(values)

    def randomize_preset(self, force=False):
        # force argument is because auto randomization (when applied to all nodes)
        # can be disabled for single nodes
        # force is set to True when preset is randomized with click on button in node context
        if len(self.spec.presets) == 0:
            return
        if not force and not self.allow_preset_randomization:
            return
        name, values = random.choice(self.spec.presets)
        self.set_preset(values)

    def reset_state(self, force=False):
        # TODO does the force parameter make sense here?!
        if force or self.allow_state_randomization:
            self.set_state(evaluate_values(self, self.spec.initial_state))
            self.force_evaluate()
    def randomize_state(self, force=False):
        if force or self.allow_state_randomization:
            self.set_state(evaluate_values(self, self.spec.random_state))
            self.force_evaluate()

    def get_extra(self):
        return {"allow_preset_randomization" : self.allow_preset_randomization}

    def set_extra(self, values):
        if "allow_preset_randomization" in values:
            self.allow_preset_randomization = values["allow_preset_randomization"]

    @classmethod
    def get_subclass_nodes(cls, include_self=True):
        nodes = []
        for node in NodeMeta.node_types:
            if not include_self and node == cls:
                continue
            if issubclass(node, cls):
                nodes.append(node)
        return nodes

    @classmethod
    def get_presets(cls, graph):
        # to be implemented by child node
        # should return list of tuples (name, values)
        #   (values as dictionary port_id => manual value)
        return []

class ValueHolder:
    @property
    def has_changed(self):
        raise NotImplementedError()
    @property
    def value(self):
        raise NotImplementedError()

    def copy_to(self, value):
        if self.has_changed_fast():
            value.value = self.value

class SettableValueHolder(ValueHolder):
    def __init__(self, default_value):
        self._value = default_value
        self._changed = True

        self.force_value = False

    @property
    def has_changed(self):
        # TODO when to reset this
        # maybe once all stages are evaluated
        # make sure stages are evaluated in right order (output stage last)
        return self._changed
    @has_changed.setter
    def has_changed(self, changed):
        self._changed = changed

    def has_changed_fast(self):
        return self._changed
    def reset_changed(self):
        self._changed = False

    @property
    def value(self):
        return self._value
    @value.setter
    def value(self, value):
        self._value = value
        self._changed = True

class InputValueHolder(ValueHolder):
    def __init__(self, manual_value):
        self.manual_value = manual_value

        # TODO storing value and the node might seem a bit weird
        # but we need the node for knowing on which nodes this depends
        # and the value so we don't have to look it up from the node every time
        self.connected_node = None
        self.connected_value = None
        self.has_connection_changed = True
    
    @property
    def is_connected(self):
        return self.connected_value is not None

    def connect(self, node, port_id):
        self.connected_node = node
        self.connected_value = node.get_value(port_id)
        self.has_connection_changed = True

    def disconnect(self):
        # make the manual input keep the value when connection is removed
        #if self.connected_value is not None:
        #    self.manual_value.value = self.connected_value.value
        self.connected_node = None
        self.connected_value = None
        self.has_connection_changed = True

    @property
    def has_changed(self):
        return (self.connected_value and self.connected_value.has_changed) or self.manual_value.has_changed or self.has_connection_changed

    @has_changed.setter
    def has_changed(self, changed):
        if not changed:
            self.has_connection_changed = False
            self.manual_value.has_changed = False

    # TODO remove property at some time and use only functions?
    # properties have some calling overhead and change check is called often
    def has_changed_fast(self):
        return (self.connected_value and self.connected_value.has_changed) or self.manual_value.has_changed or self.has_connection_changed

    def reset_changed(self):
        self.has_connection_changed = False
        self.manual_value.reset_changed()

    @property
    def value(self):
        connected_value = self.connected_value
        manual_value = self.manual_value
        # the manual value (like with button widget) can force a value
        if connected_value is not None and not manual_value.force_value:
            return connected_value.value
        return manual_value.value

    @value.setter
    def value(self, value):
        self.manual_value.value = value

