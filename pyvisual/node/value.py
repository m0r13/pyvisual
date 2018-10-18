import numpy as np
from pyvisual.node.base import Node
from pyvisual.node import dtype
from pyvisual.editor import widget

class InputBool(Node):
    class Meta:
        outputs = [
            {"name" : "output", "dtype" : dtype.bool, "widgets" : [widget.Bool], "manual_input" : True}
        ]
        options = {
            "category" : "input",
            "show_title" : False
        }

class OutputBool(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.bool, "widgets" : [widget.Bool], "manual_input" : False}
        ]
        options = {
            "category" : "output",
            "show_title" : False
        }

class InputEvent(Node):
    class Meta:
        outputs = [
            {"name" : "output", "dtype" : dtype.event, "widgets" : [widget.Button], "manual_input" : True}
        ]
        options = {
            "category" : "input",
            "show_title" : False
        }

class OutputEvent(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.event, "widgets" : [widget.Button], "manual_input" : False}
        ]
        options = {
            "category" : "output",
            "show_title" : False
        }

class InputFloat(Node):
    class Meta:
        outputs = [
            {"name" : "output", "dtype" : dtype.float, "widgets" : [widget.Float], "manual_input" : True}
        ]
        options = {
            "category" : "input",
            "show_title" : False
        }

class OutputFloat(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.float, "widgets" : [widget.Float], "manual_input" : False}
        ]
        options = {
            "category" : "output",
            "show_title" : False
        }

class InputColor(Node):
    class Meta:
        outputs = [
            {"name" : "output", "dtype" : dtype.color, "widgets" : [widget.Color], "manual_input" : True},
        ]
        options = {
            "category" : "input",
            "show_title" : False
        }

class OutputColor(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.color, "widgets" : [widget.Color], "manual_input" : False},
        ]
        options = {
            "category" : "output",
            "show_title" : False
        }

class Float2Color(Node):
    class Meta:
        inputs = [
            {"name" : "r", "dtype" : dtype.float, "widgets" : [lambda node: widget.Float(node, minmax=(0.0, 1.0))]},
            {"name" : "g", "dtype" : dtype.float, "widgets" : [lambda node: widget.Float(node, minmax=(0.0, 1.0))]},
            {"name" : "b", "dtype" : dtype.float, "widgets" : [lambda node: widget.Float(node, minmax=(0.0, 1.0))]},
            {"name" : "a", "dtype" : dtype.float, "widgets" : [lambda node: widget.Float(node, minmax=(0.0, 1.0))], "default" : 1.0},
        ]
        outputs = [
            {"name" : "color", "dtype" : dtype.color, "widgets" : [widget.Color]},
        ]
        options = {
            "category" : "conversion",
            "show_title" : True
        }

    def _evaluate(self):
        self.set("color", np.array([
            self.get("r"),
            self.get("g"),
            self.get("b"),
            self.get("a")
        ], dtype=np.float32))

class Color2Float(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.color, "widgets" : [widget.Color]},
        ]
        outputs = [
            {"name" : "r", "dtype" : dtype.float, "widgets" : [lambda node: widget.Float(node, minmax=(0.0, 1.0))]},
            {"name" : "g", "dtype" : dtype.float, "widgets" : [lambda node: widget.Float(node, minmax=(0.0, 1.0))]},
            {"name" : "b", "dtype" : dtype.float, "widgets" : [lambda node: widget.Float(node, minmax=(0.0, 1.0))]},
            {"name" : "a", "dtype" : dtype.float, "widgets" : [lambda node: widget.Float(node, minmax=(0.0, 1.0))], "default" : 1.0},
        ]
        options = {
            "category" : "conversion",
            "show_title" : True
        }

    def _evaluate(self):
        color = self.get("input")
        self.set("r", color[0])
        self.set("g", color[1])
        self.set("b", color[2])
        self.set("a", color[3])

