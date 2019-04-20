import math
import numpy as np
from pyvisual.node.base import Node
from pyvisual.node import dtype

def dot(input_transform, transform):
    return np.dot(transform, input_transform)

class Scale(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.mat4},
            {"name" : "x", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "y", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "uniform", "dtype" : dtype.bool, "dtype_args" : {"default" : True}, "group" : "additional"},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.mat4},
        ]

    def _evaluate(self):
        uniform = self.get("uniform")
        input_x = self.get_input("x")
        input_y = self.get_input("y")
        if uniform and input_x.has_changed:
            input_y.value = input_x.value
        elif uniform and input_y.has_changed:
            input_x.value = input_y.value

        transform = np.array([[self.get("x"), 0.0, 0.0, 0.0],
                              [0.0, self.get("y"), 0.0, 0.0],
                              [0.0, 0.0, 1.0, 0.0],
                              [0.0, 0.0, 0.0, 1.0]], dtype=np.float32).T
        self.set("output", dot(self.get("input"), transform))

class Rotate(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.mat4},
            {"name" : "theta", "dtype" : dtype.float, "dtype_args": {"unit" : "deg"}},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.mat4},
        ]

    def _evaluate(self):
        theta = math.radians(self.get("theta"))
        sinT = math.sin(theta)
        cosT = math.cos(theta)
        transform = np.array([[cosT, -sinT, 0.0, 0.0],
                              [sinT, cosT, 0.0, 0.0],
                              [0.0, 0.0, 1.0, 0.0],
                              [0.0, 0.0, 0.0, 1.0]], dtype=np.float32).T
        self.set("output", dot(self.get("input"), transform))

class Translate(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.mat4},
            {"name" : "x", "dtype" : dtype.float, "dtype_args" : {"unit" : "px"}},
            {"name" : "y", "dtype" : dtype.float, "dtype_args" : {"unit" : "px"}},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.mat4},
        ]

    def _evaluate(self):
        transform = np.array([[1.0, 0.0, 0.0, self.get("x")],
                              [0.0, 1.0, 0.0, self.get("y")],
                              [0.0, 0.0, 1.0, 0.0],
                              [0.0, 0.0, 0.0, 1.0]], dtype=np.float32).T
        self.set("output", dot(self.get("input"), transform))

class Dot(Node):
    class Meta:
        inputs = [
            {"name" : "t1", "dtype" : dtype.mat4},
            {"name" : "t2", "dtype" : dtype.mat4},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.mat4},
        ]

    def _evaluate(self):
        self.set("output", np.dot(self.get("t1"), self.get("t2")))

