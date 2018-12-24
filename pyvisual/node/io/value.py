import numpy as np
from pyvisual.node.base import Node
from pyvisual.node import dtype

class InputBool(Node):
    class Meta:
        outputs = [
            {"name" : "output", "dtype" : dtype.bool, "manual_input" : True}
        ]
        options = {
            "category" : "input",
            "show_title" : False
        }

class OutputBool(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.bool, "manual_input" : False}
        ]
        options = {
            "category" : "output",
            "show_title" : False
        }

class InputEvent(Node):
    class Meta:
        outputs = [
            {"name" : "output", "dtype" : dtype.event, "manual_input" : True}
        ]
        options = {
            "category" : "input",
            "show_title" : False
        }

class OutputEvent(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.event, "manual_input" : False}
        ]
        options = {
            "category" : "output",
            "show_title" : False
        }

class InputFloat(Node):
    class Meta:
        outputs = [
            {"name" : "output", "dtype" : dtype.float, "manual_input" : True}
        ]
        options = {
            "category" : "input",
            "show_title" : False
        }

class OutputFloat(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.float, "manual_input" : False}
        ]
        options = {
            "category" : "output",
            "show_title" : False
        }

class InputColor(Node):
    class Meta:
        outputs = [
            {"name" : "output", "dtype" : dtype.color, "manual_input" : True},
        ]
        options = {
            "category" : "input",
            "show_title" : False
        }

class OutputColor(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.color, "manual_input" : False},
        ]
        options = {
            "category" : "output",
            "show_title" : False
        }

class Float2Vec2(Node):
    class Meta:
        inputs = [
            {"name" : "x", "dtype" : dtype.float, "dtype_args" : {}},
            {"name" : "y", "dtype" : dtype.float, "dtype_args" : {}},
        ]
        outputs = [
            {"name" : "vec2", "dtype" : dtype.vec2},
        ]
        options = {
            "category" : "conversion",
            "show_title" : True
        }

    def _evaluate(self):
        self.set("vec2", np.array([
            self.get("x"),
            self.get("y")
        ], dtype=np.float32))

class Float2Color(Node):
    class Meta:
        inputs = [
            {"name" : "r", "dtype" : dtype.float, "dtype_args" : {"range" : (0.0, 1.0)}},
            {"name" : "g", "dtype" : dtype.float, "dtype_args" : {"range" : (0.0, 1.0)}},
            {"name" : "b", "dtype" : dtype.float, "dtype_args" : {"range" : (0.0, 1.0)}},
            {"name" : "a", "dtype" : dtype.float, "dtype_args" : {"range" : (0.0, 1.0), "default" : 1.0}},
        ]
        outputs = [
            {"name" : "color", "dtype" : dtype.color},
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

class Vec22Float(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.vec2},
        ]
        outputs = [
            {"name" : "x", "dtype" : dtype.float},
            {"name" : "y", "dtype" : dtype.float},
        ]
        options = {
            "category" : "conversion",
            "show_title" : True
        }

    def _evaluate(self):
        vec = self.get("input")
        self.set("x", vec[0])
        self.set("y", vec[1])

class Color2Float(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.color},
        ]
        outputs = [
            {"name" : "r", "dtype" : dtype.float, "dtype_args" : {"range" : (0.0, 1.0)}},
            {"name" : "g", "dtype" : dtype.float, "dtype_args" : {"range" : (0.0, 1.0)}},
            {"name" : "b", "dtype" : dtype.float, "dtype_args" : {"range" : (0.0, 1.0)}},
            {"name" : "a", "dtype" : dtype.float, "dtype_args" : {"range" : (0.0, 1.0), "default" : 1.0}},
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

