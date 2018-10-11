
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
        meta.node_types.append(cls)
        print("Registered node type: %s" % cls)
        return cls

class NodeSpec:
    def __init__(self, cls=None, inputs=None, outputs=None, options={}):
        self.cls = cls
        self.inputs = inputs if inputs is not None else []
        self.outputs = outputs if outputs is not None else []
        self.options = dict(options)

    @property
    def name(self):
        return self.cls.__name__

    def append(self, child_spec):
        self.cls = child_spec.cls
        self.inputs = self.inputs + child_spec.inputs
        self.outputs = self.outputs + child_spec.outputs
        self.options.update(child_spec.options)

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
            options = getattr(cls.Meta, "options", {})
            return NodeSpec(cls=cls, inputs=inputs, outputs=outputs, options=options)
        
        spec = NodeSpec()
        for cls in bases:
            spec.append(parse(cls))

        # set spec defaults at last
        spec.options.setdefault("virtual", False)
        spec.options.setdefault("category", "")
        spec.options.setdefault("show_title", True)
        for port_spec in spec.inputs + spec.outputs:
            port_spec.setdefault("default", None)
            port_spec.setdefault("widgets", [])
        return spec

class Node(metaclass=NodeMeta):
    class Meta:
        inputs = []
        outputs = []

    def __init__(self, always_evaluate=False):
        self.always_evaluate = always_evaluate
        self._evaluated = False
        self._first_evaluated = False

        self.manual_inputs = {}
        self.inputs = {}
        self.outputs = {}

        spec = self.get_node_spec()
        for port_spec in spec.inputs:
            default = port_spec["default"]
            if default is None:
                default = port_spec["dtype"].default()
            manual_input = SettableValueHolder(default)
            self.manual_inputs[port_spec["name"]] = manual_input
            self.inputs[port_spec["name"]] = InputValueHolder(manual_input)
        for port_spec in spec.outputs:
            default = port_spec["default"]
            if default is None:
                default = port_spec["dtype"].default()
            self.outputs[port_spec["name"]] = SettableValueHolder(default)

    @property
    def input_nodes(self):
        nodes = set()
        for input_value in self.inputs.values():
            if input_value.is_connected:
                nodes.add(input_value.connected_node)
        return nodes

    @property
    def needs_evaluation(self):
        # if any input has changed
        return not self._first_evaluated or any(map(lambda v: v.has_changed, self.inputs.values()))

    @property
    def evaluated(self):
        return self._evaluated
    @evaluated.setter
    def evaluated(self, evaluated):
        # at the beginning of each run where all nodes are not evaluated yet
        # all values will be set unchanged so changes in evaluating nodes will
        # result in the nodes after them to be evaluated accordingly
        if not evaluated:
            for value in self.outputs.values():
                value.has_changed = False
            for value in self.inputs.values():
                value.has_changed = False
        self._evaluated = evaluated

    def get(self, name):
        return self.inputs[name].value
    def set(self, name, value):
        self.outputs[name].value = value

    def process(self):
        # update a node
        # return if node needed update
        if not self.evaluated and (self.needs_evaluation or self.always_evaluate):
            self._evaluate()
            self._evaluated = True
            self._first_evaluated = True
            return True
        return False

    def _evaluate(self):
        # to be implemented by child nodes
        # never call from outside! use process() instead
        pass

    def _show_custom_ui(self):
        pass

    @classmethod
    def get_node_spec(cls):
        return NodeSpec.from_cls(cls)

    @classmethod
    def get_sub_nodes(cls, include_self=True):
        nodes = []
        for node in NodeMeta.node_types:
            if not include_self and node == cls:
                continue
            if issubclass(node, cls):
                nodes.append(node)
        return nodes

class ValueHolder:
    @property
    def has_changed(self):
        raise NotImplementedError()
    @property
    def value(self):
        raise NotImplementedError()

class SettableValueHolder(ValueHolder):
    def __init__(self, default_value):
        self._value = default_value
        self._changed = False

    @property
    def has_changed(self):
        # TODO when to reset this
        # maybe once all stages are evaluated
        # make sure stages are evaluated in right order (output stage last)
        return self._changed
    @has_changed.setter
    def has_changed(self, changed):
        self._changed = changed

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
        self.connection_changed = False
    
    @property
    def is_connected(self):
        return self.connected_value is not None

    def connect(self, node, output):
        self.connected_node = node
        self.connected_value = node.outputs[output]
        self.connection_changed = True

    def disconnect(self):
        # make the manual input keep the value when connection is removed
        if self.connected_value is not None:
            self.manual_value.value = self.connected_value.value
        self.connected_node = None
        self.connected_value = None
        self.connection_changed = True

    @property
    def has_changed(self):
        if self.connection_changed:
            return True
        connected_changed = self.connected_value.has_changed if self.connected_value else False
        manual_changed = self.manual_value.has_changed
        return connected_changed or manual_changed

    @has_changed.setter
    def has_changed(self, changed):
        # TODO hmm this seems like a hack
        #if not changed:
        #    self.connection_changed = False
        pass

    @property
    def value(self):
        if self.connected_value is not None:
            return self.connected_value.value
        return self.manual_value.value

