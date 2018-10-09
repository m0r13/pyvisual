import numpy as np
from pyvisual.node.base import Node
from pyvisual.node import dtype

class InputFloat(Node):
    class Meta:
        outputs = [
            {"name" : "output", "dtype" : dtype.float, "show_label" : False}
        ]
        options = {
            "category" : "input",
            "show_title" : False
        }

class OutputFloat(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.float, "show_label" : False}
        ]
        options = {
            "category" : "output",
            "show_title" : False
        }

class InputColor(Node):
    class Meta:
        outputs = [
            {"name" : "output", "dtype" : dtype.vec4, "show_label" : False},
        ]
        options = {
            "category" : "input",
            "show_title" : False
        }

class OutputColor(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.vec4, "show_label" : False},
        ]
        options = {
            "category" : "output",
            "show_title" : False
        }

class Float2Color(Node):
    class Meta:
        inputs = [
            {"name" : "r", "dtype" : dtype.float, "show_label" : False},
            {"name" : "g", "dtype" : dtype.float, "show_label" : False},
            {"name" : "b", "dtype" : dtype.float, "show_label" : False},
            {"name" : "a", "dtype" : dtype.float, "show_label" : False},
        ]
        outputs = [
            {"name" : "color", "dtype" : dtype.vec4, "show_label" : False},
        ]
        options = {
            "category" : "conversion",
            "show_title" : True
        }

    def evaluate(self):
        self.set("color", np.array([
            self.get("r"),
            self.get("g"),
            self.get("b"),
            self.get("a")
        ], dtype=np.float32))

class Color2Float(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.vec4, "show_label" : False},
        ]
        outputs = [
            {"name" : "r", "dtype" : dtype.float, "show_label" : False},
            {"name" : "g", "dtype" : dtype.float, "show_label" : False},
            {"name" : "b", "dtype" : dtype.float, "show_label" : False},
            {"name" : "a", "dtype" : dtype.float, "show_label" : False},
        ]
        options = {
            "category" : "conversion",
            "show_title" : True
        }

    def evaluate(self):
        color = self.get("input")
        self.set("r", color[0])
        self.set("g", color[1])
        self.set("b", color[2])
        self.set("a", color[3])

