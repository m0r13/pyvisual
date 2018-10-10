from pyvisual.node.base import Node
from pyvisual.node import dtype
from pyvisual.editor import widget

class Render(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.tex2d, "widgets" : [widget.Texture()]}
        ]
        outputs = []
        options = {
            "category" : "output",
        }

class InputTexture(Node):
    class Meta:
        outputs = [
            {"name" : "output", "dtype" : dtype.tex2d, "widgets" : [widget.Texture()]},
        ]
        options = {
            "category" : "input"
        }
