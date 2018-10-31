import math
import numpy as np
import traceback
import random
import imgui
from pyvisual.node.base import Node
from pyvisual.node.op.gpu.base import Shader
from pyvisual.node import dtype
from pyvisual.editor import widget
from pyvisual import assets
from glumpy import gloo, gl, glm
from PIL import Image

# TODO
dummy = np.zeros((1, 1, 4), dtype=np.uint8).view(gloo.Texture2D)

class MixTexture(Shader):
    class Meta:
        inputs = [
            {"name" : "destination", "dtype" : dtype.tex2d},
            {"name" : "alpha", "dtype" : dtype.float, "dtype_args" : {"range" : [0, 1]}},
        ]
        options = {
            "virtual" : True,
            "category" : "shader"
        }

    def set_uniforms(self, program):
        source = self.get("destination")
        if source is None:
            program["uDestinationTexture"] = dummy
            return
        program["uDestinationTexture"] = source
        program["uAlpha"] = self.get("alpha")

class LerpMixTexture(MixTexture):
    class Meta:
        options = {
            "virtual" : False,
            "category" : "shader"
        }

    def __init__(self):
        super().__init__("common/passthrough.vert", "transition/lerp.frag")

class MoveMixTexture(MixTexture):
    class Meta:
        inputs = [
            {"name" : "x", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "y", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
        ]
        options = {
            "virtual" : False,
            "category" : "shader"
        }

    def __init__(self):
        super().__init__("common/passthrough.vert", "transition/move.frag")

    def set_uniforms(self, program):
        super().set_uniforms(program)

        program["uDirection"] = (self.get("x"), self.get("y"))

class SwipeMixTexture(MixTexture):
    class Meta:
        inputs = [
            {"name" : "x", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "y", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
        ]
        options = {
            "virtual" : False,
            "category" : "shader"
        }

    def __init__(self):
        super().__init__("common/passthrough.vert", "transition/swipe.frag")

    def set_uniforms(self, program):
        super().set_uniforms(program)

        program["uDirection"] = (self.get("x"), self.get("y"))

# TODO node restructuring
from pyvisual.node.generate import scalable_timer
class TransitionTimer(Node):
    class Meta:
        inputs = [
            {"name" : "duration", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "trigger", "dtype" : dtype.event},
            {"name" : "reverse", "dtype" : dtype.bool, "dtype_args" : {"default" : 1.0}},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float},
        ]

    def __init__(self):
        super().__init__(always_evaluate=True)

        self.time = scalable_timer()

    def _evaluate(self):
        duration = self.get("duration")
        scale = float("inf") if duration == 0.0 else 1.0 / duration
        t = 0.0
        #if self.get("trigger"):
        #    self.always_evaluate = True
        if self.get("reverse"):
            t = max(0.0, 1.0 - self.time(scale, self.get("trigger")))
            #if t < 0.00001:
            #    self.always_evaluate = False
        else:
            t = min(1.0, self.time(scale, self.get("trigger")))
            #if t > 1.0 - 0.00001:
            #    self.always_evaluate = False
        self.set("output", t)

