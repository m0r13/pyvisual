#!/usr/bin/env python3

class NodeMeta(type):
    node_types = []

    def __new__(meta, name, bases, dct):
        assert len(bases) <= 1, "Node class may have only up to one base node"
        dct["base_node"] = bases[0] if len(bases) else None
        cls = super().__new__(meta, name, bases, dct)
        meta.node_types.append(cls)
        print("Created clasis %s, bases %s" % (str(cls), str(list(bases))))
        return cls

class NodeSpec:
    def __init__(self, cls=None, inputs=None, outputs=None, options={}):
        self.cls = cls
        self.inputs = inputs if inputs is not None else []
        self.outputs = outputs if outputs is not None else []
        self.options = dict(options)
        self.options.setdefault("show_title", True)

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
        self.outputs = OutputMap()

    @property
    def evaluated(self):
        return self.evaluated
    @evaluated.setter
    def evaluated(self, evaluated):
        # TODO somehow set that input nodes need to be evaluated?
        self.evaluated = evaluated

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

# TODO I think we don't need this after all
# a dict with port_id -> settable value should do it
class OutputMap:
    def __init__(self):
        self.values = {}
        self.changed = {}

    def has_value(self, name):
        return self.get(name) is not None

    def has_changed(self, name):
        # TODO how and when to unset this?
        return self.changed.get(name, False)

    def get(self, name):
        return self.values.get(name)

    def set(self, name, value):
        self.values[name] = value
        self.set_changed(name)

    def set_changed(self, name):
        self.changed[name] = True

class ValueHolder:
    @property
    def has_value(self):
        raise NotImplementedError()
    @property
    def has_changed(self):
        raise NotImplementedError()
    @property
    def value(self):
        raise NotImplementedError()

class SettableValueHolder(ValueHolder):
    def __init__(self):
        self._value = None
        self._changed = False

    @property
    def has_value(self):
        return self.value is not None

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

class OverrideValueHolder(ValueHolder):
    def __init__(self, value, override):
        self.value = value
        self.override = override

    @property
    def current(self):
        if self.override.has_value:
            return self.override
        elif self.value.has_value:
            return self.value
        # TODO ?
        return None

    @property
    def has_value(self):
        return self.override.has_value or self.value.has_value

    @property
    def has_changed(self):
        current = self.current
        if current is None:
            # TODO should return True when current changes
            return False
        return current.has_changed

    @property
    def value(self):
        current = self.current
        assert current is not None, "no value assigned"
        return current.value

class ConnectionValueHolder(ValueHolder):
    def __init__(self, node, name):
        self.node = node
        self.name = name

    @property
    def has_value(self):
        return self.node.outputs[name].has_value
    @property
    def has_changed(self):
        return self.node.outputs[name].has_changed
    @property
    def value(self):
        return self.node.outputs[name].value

class TestNode(Node):
    class Meta:
        inputs = ["test_input"]
        outputs = ["test_output"]

class SubNode(TestNode):
    class Meta:
        inputs = ["sub_input"]
        outputs = ["another_output"]

class VisualNode(Node):
    class Meta:
        pass

class ShaderNode(VisualNode):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : "tex2d"}
        ]
        outputs = [
            {"name" : "output", "dtype" : "tex2d"}
        ]

class EffectMirrorNode(ShaderNode):
    class Meta:
        inputs = [
            {"name" : "mode", "dtype" : "float"}
        ]
        outputs = [
            {"name" : "test2", "dtype" : "tex2"},
            {"name" : "output", "dtype" : "tex2"}
        ]

class EffectHuePhaseNode(ShaderNode):
    class Meta:
        inputs = [
            {"name" : "hue", "dtype" : "float"}
        ]
        outputs = []

class RendererNode(VisualNode):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : "tex2d"}
        ]
        outputs = []

class TextureNode(VisualNode):
    class Meta:
        inputs = []
        outputs = [
            {"name" : "output", "dtype" : "tex2d"}
        ]

class ValueNode(VisualNode):
    class Meta:
        inputs = []
        outputs = [
            {"name" : "output", "dtype" : "float"}
        ]
        options = {
            "show_title" : False
        }

class TestNode(VisualNode):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : "tex2d"},
            {"name" : "input", "dtype" : "tex2d"},
            {"name" : "input", "dtype" : "float"},
        ]
        outputs = [
            {"name" : "output", "dtype" : "float"},
        ]

if __name__ == "__main__":
    print(Node.get_node_spec())
    print(SubNode.get_node_spec())
    print([ n.get_node_spec().name for n in VisualNode.get_sub_nodes() ])
    print(ShaderNode.get_node_spec())
