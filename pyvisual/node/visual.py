from pyvisual.node.base import Node

class RendererNode(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : "tex2d"}
        ]
        outputs = []
        options = {
            "category" : "output",
        }

