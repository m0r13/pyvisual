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
    def __init__(self, name="", inputs=None, outputs=None):
        self.name = name
        self.inputs = inputs if inputs is not None else []
        self.outputs = outputs if outputs is not None else []

    def append(self, child_spec):
        self.name = child_spec.name
        self.inputs = self.inputs + child_spec.inputs
        self.outputs = self.outputs + child_spec.outputs

    def __repr__(self):
        return "NodeSpec(name='%s', inputs=%s, outputs=%s)" % (self.name, self.inputs, self.outputs)

    @staticmethod
    def from_cls(node_cls):
        bases = []
        base_cls = node_cls
        bases.insert(0, base_cls)
        while base_cls is not None:
            bases.insert(0, base_cls)
            base_cls = base_cls.base_node

        def parse(cls):
            m = cls.Meta
            return NodeSpec(name=m.name, inputs=m.inputs, outputs=m.outputs)
        spec = NodeSpec()
        for cls in bases:
            spec.append(parse(cls))
        return spec

class Node(metaclass=NodeMeta):
    class Meta:
        name = "Node"
        inputs = []
        outputs = []

    @classmethod
    def get_node_spec(cls):
        return NodeSpec.from_cls(cls)

class TestNode(Node):
    class Meta:
        name = "TestNode"
        inputs = ["test_input"]
        outputs = ["test_output"]

class SubNode(TestNode):
    class Meta:
        name = "SubNode"
        inputs = ["sub_input"]
        outputs = ["another_output"]

if __name__ == "__main__":
    print(Node.get_node_spec())
    print(SubNode.get_node_spec())
