import imgui
from pyvisual.node.base import Node
from pyvisual.node import dtype
from pyvisual.audio import analyzer

class Plot(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.float},
            {"name" : "min", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "max", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "time", "dtype" : dtype.float, "dtype_args" : {"default" : 5.0}},
        ]
        options = {
            "category" : "math",
            "virtual" : False
        }

    def __init__(self):
        super().__init__(always_evaluate=True)
        self.buffer = analyzer.RingBuffer(5*60)

    def _evaluate(self):
        self.buffer.append(self.get("input"))

    def _show_custom_ui(self):
        imgui.plot_lines("", self.buffer.contents, float(self.get("min")), float(self.get("max")), (200, 50))

