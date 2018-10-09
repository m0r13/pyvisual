from pyvisual.node.base import Node

class ValueAddNode(Node):
    class Meta:
        inputs = [
            {"name" : "v0", "dtype" : "float", "show_label" : False},
            {"name" : "v1", "dtype" : "float", "show_label" : False}
        ]
        outputs = [
            {"name" : "output", "dtype" : "float", "show_label" : False}
        ]
        options = {
            "category" : "math",
        }

    def evaluate(self):
        self.outputs["output"].value = self.inputs["v0"].value + self.inputs["v1"].value

