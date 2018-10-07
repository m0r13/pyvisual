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
    def __init__(self, cls=None, inputs=None, outputs=None):
        self.cls = cls
        self.inputs = inputs if inputs is not None else []
        self.outputs = outputs if outputs is not None else []

    @property
    def name(self):
        return self.cls.__name__

    def append(self, child_spec):
        self.cls = child_spec.cls
        self.inputs = self.inputs + child_spec.inputs
        self.outputs = self.outputs + child_spec.outputs

    def __repr__(self):
        return "NodeSpec(cls=%s, inputs=%s, outputs=%s)" % (self.cls, self.inputs, self.outputs)

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
            return NodeSpec(cls=cls, inputs=inputs, outputs=outputs)
        spec = NodeSpec()
        for cls in bases:
            spec.append(parse(cls))
        return spec

class Node(metaclass=NodeMeta):
    class Meta:
        inputs = []
        outputs = []

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
        ]

class EffectHuePhaseNode(ShaderNode):
    class Meta:
        inputs = [
            {"name" : "hue", "dtype" : "float"}
        ]
        outputs = []

class ScreenOutputNode(VisualNode):
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

if __name__ == "__main__":
    print(Node.get_node_spec())
    print(SubNode.get_node_spec())
    print([ n.get_node_spec().name for n in VisualNode.get_sub_nodes() ])
    print(ShaderNode.get_node_spec())
