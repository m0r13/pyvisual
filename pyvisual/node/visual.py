from pyvisual.node.base import Node
from pyvisual.node import dtype

class Render(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.tex2d}
        ]
        outputs = []
        options = {
            "category" : "output",
        }

class InputTexture(Node):
    class Meta:
        outputs = [
            {"name" : "output", "dtype" : dtype.tex2d},
        ]
        options = {
            "category" : "input",
            "show_title" : False
        }
