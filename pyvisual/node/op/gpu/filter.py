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

class Glitch(Shader):
    class Meta:
        inputs = [
            {"name" : "time", "dtype" : dtype.float},
            {"name" : "amount", "dtype" : dtype.float},
            {"name" : "speed", "dtype" : dtype.float},
        ]
        options = {
            "virtual" : False,
            "category" : "shader"
        }

    def __init__(self):
        super().__init__("common/passthrough.vert", "post/glitch.frag")

    def set_uniforms(self, program):
        program["time"] = self.get("time")
        program["amount"] = self.get("amount")
        program["speed"] = self.get("speed")

WRAPPING_MODES = ["repeat", "mirrored repeat", "clamp to edge", "clamp to border"]
WRAPPING_MODES_GL = [gl.GL_REPEAT, gl.GL_MIRRORED_REPEAT, gl.GL_CLAMP_TO_EDGE, gl.GL_CLAMP_TO_BORDER]
INTERPOLATION_MODES = ["nearest", "linear"]
INTERPOLATION_MODES_GL = [gl.GL_NEAREST, gl.GL_LINEAR]
class SampleTexture(Shader):
    class Meta:
        inputs = [
            {"name" : "wrapping", "dtype" : dtype.int, "dtype_args" : {"default" : 1, "choices" : WRAPPING_MODES}},
            {"name" : "interpolation", "dtype" : dtype.int, "dtype_args" : {"default" : 1, "choices" : INTERPOLATION_MODES}},
        ]
        options = {
            "virtual" : False,
            "category" : "shader"
        }

    def __init__(self):
        super().__init__("common/passthrough.vert", "common/passthrough.frag")

    def set_uniforms(self, program):
        wrapping_mode = int(self.get("wrapping"))
        if wrapping_mode < 0 or wrapping_mode >= len(WRAPPING_MODES):
            wrapping_mode = 0
        interpolation_mode = int(self.get("interpolation"))
        if interpolation_mode < 0 or interpolation_mode >= len(INTERPOLATION_MODES):
            interpolation_mode = 0
        input_texture = self.get("input")
        input_texture.wrapping = WRAPPING_MODES_GL[wrapping_mode]
        input_texture.interpolation = INTERPOLATION_MODES_GL[interpolation_mode]

class Mirror(Shader):
    class Meta:
        inputs = [
            {"name" : "mode", "dtype" : dtype.int, "dtype_args" : {"range" : [0, 3]}},
        ]
        options = {
            "virtual" : False,
            "category" : "shader"
        }

    def __init__(self):
        super().__init__("common/passthrough.vert", "post/mirror.frag")

    def set_uniforms(self, program):
        program["uMode"] = int(self.get("mode"))

class PolarMirror(Shader):
    class Meta:
        inputs = [
            {"name" : "axis_angle", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "angle", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "segments", "dtype" : dtype.int, "dtype_args" : {"default" : 5.0}},
        ]
        options = {
            "virtual" : False,
            "category" : "shader"
        }

    def __init__(self):
        super().__init__("common/passthrough.vert", "post/mirror_polar.frag")

    def set_uniforms(self, program):
        input_texture = self.get("input")
        input_texture.wrapping = gl.GL_MIRRORED_REPEAT
        program["uAxisAngle"] = self.get("axis_angle")
        program["uAngleOffset"] = self.get("angle")
        program["uSegmentCount"] = self.get("segments")

class Slices(Shader):
    class Meta:
        inputs = [
            {"name" : "slices", "dtype" : dtype.int, "dtype_args" : {"default" : 3.0}},
            {"name" : "offset", "dtype" : dtype.float, "dtype_args" : {"default" : 100.0}},
            {"name" : "timeH", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "timeV", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
        ]
        options = {
            "virtual" : False,
            "category" : "shader"
        }

    def __init__(self):
        super().__init__("common/passthrough.vert", "post/slices.frag")

    def set_uniforms(self, program):
        input_texture = self.get("input")
        input_texture.wrapping = gl.GL_MIRRORED_REPEAT
        for name in ("slices", "offset", "timeH", "timeV"):
            program[name] = self.get(name)

class ScanlinesFine(Shader):
    class Meta:
        inputs = [
            {"name" : "time", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "count", "dtype" : dtype.float, "dtype_args" : {"default" : 50.0}},
            {"name" : "noiseAmount", "dtype" : dtype.float, "dtype_args" : {"default" : 0.01}},
            {"name" : "linesAmount", "dtype" : dtype.float, "dtype_args" : {"default" : 0.01}},
        ]
        options = {
            "virtual" : False,
            "category" : "shader"
        }

    def __init__(self):
        super().__init__("common/passthrough.vert", "post/scanlinesfine.frag")

    def set_uniforms(self, program):
        input_texture = self.get("input")
        input_texture.wrapping = gl.GL_MIRRORED_REPEAT
        for name in ("time", "count", "noiseAmount", "linesAmount"):
            program[name] = self.get(name)

