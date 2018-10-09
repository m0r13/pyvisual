
class NodeMeta(type):
    node_types = []

    def __new__(meta, name, bases, dct):
        assert len(bases) <= 1, "Node class may have only up to one base node"
        dct["base_node"] = bases[0] if len(bases) else None
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
        self.options.setdefault("category", "")
        self.options.setdefault("show_title", True)
        for port_spec in self.inputs + self.outputs:
            port_spec.setdefault("show_label", True)

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
        return spec

class Node(metaclass=NodeMeta):
    class Meta:
        inputs = []
        outputs = []

    def __init__(self):
        self._evaluated = False

        self.manual_inputs = {}
        self.inputs = {}
        self.outputs = {}

        spec = self.get_node_spec()
        for port_spec in spec.inputs:
            manual_input = SettableValueHolder(0.0)
            self.manual_inputs[port_spec["name"]] = manual_input
            self.inputs[port_spec["name"]] = InputValueHolder(manual_input)
        for port_spec in spec.outputs:
            self.outputs[port_spec["name"]] = SettableValueHolder(0.0)

    @property
    def input_nodes(self):
        nodes = set()
        for input_value in self.inputs.values():
            if input_value.is_connected:
                nodes.add(input_value.connected_node)
        return nodes

    @property
    def evaluated(self):
        return self._evaluated
    @evaluated.setter
    def evaluated(self, evaluated):
        # TODO somehow set that input nodes need to be evaluated?
        self._evaluated = evaluated

    def evaluate(self):
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
    def __init__(self, value=0.0):
        # TODO default value
        self._value = value
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
        # TODO when to reset connection changed??
        if self.connection_changed:
            return True
        if self.connected_value is not None:
            return self.connected_value.has_changed
        return self.manual_value.has_changed

    @property
    def value(self):
        if self.connected_value is not None:
            return self.connected_value.value
        return self.manual_value.value

