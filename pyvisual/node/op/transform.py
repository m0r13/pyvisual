import math
import numpy as np
from pyvisual.node.base import Node
from pyvisual.node import dtype

class Scale(Node):
    class Meta:
        inputs = [
            {"name" : "x", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "y", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.mat4},
        ]

    def _evaluate(self):
        transform = np.array([[self.get("x"), 0.0, 0.0, 0.0],
                              [0.0, self.get("y"), 0.0, 0.0],
                              [0.0, 0.0, 1.0, 0.0],
                              [0.0, 0.0, 0.0, 1.0]], dtype=np.float32).T
        self.set("output", transform)

class UniformScale(Node):
    class Meta:
        inputs = [
            {"name" : "xy", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.mat4},
        ]

    def _evaluate(self):
        xy = self.get("xy")
        transform = np.array([[xy, 0.0, 0.0, 0.0],
                              [0.0, xy, 0.0, 0.0],
                              [0.0, 0.0, 1.0, 0.0],
                              [0.0, 0.0, 0.0, 1.0]], dtype=np.float32).T
        self.set("output", transform)

class Rotate(Node):
    class Meta:
        inputs = [
            {"name" : "theta", "dtype" : dtype.float},
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
        self.set("output", transform)

class Translate(Node):
    class Meta:
        inputs = [
            {"name" : "x", "dtype" : dtype.float},
            {"name" : "y", "dtype" : dtype.float},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.mat4},
        ]

    def _evaluate(self):
        transform = np.array([[1.0, 0.0, 0.0, self.get("x")],
                              [0.0, 1.0, 0.0, self.get("y")],
                              [0.0, 0.0, 1.0, 0.0],
                              [0.0, 0.0, 0.0, 1.0]], dtype=np.float32).T
        self.set("output", transform)

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

