import math
import numpy as np
import traceback
import random
import imgui
from pyvisual.node.base import Node
from pyvisual.node.op.gpu.base import Shader
from pyvisual.node.op.module import Module
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

class SampleTexture(Shader):
    class Meta:
        inputs = [
        ]
        options = {
            "virtual" : False,
            "category" : "shader"
        }

    def __init__(self):
        super().__init__("common/passthrough.vert", "common/passthrough.frag")

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
        input_texture = self.input_texture
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
        input_texture = self.input_texture
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
        input_texture = self.input_texture
        input_texture.wrapping = gl.GL_MIRRORED_REPEAT
        for name in ("time", "count", "noiseAmount", "linesAmount"):
            program[name] = self.get(name)

class ChromaticAberration(Shader):
    class Meta:
        inputs = [
            {"name" : "uRedOffset", "dtype" : dtype.vec2},
            {"name" : "uGreenOffset", "dtype" : dtype.vec2},
            {"name" : "uBlueOffset", "dtype" : dtype.vec2},
        ]
        options = {
            "virtual" : False,
            "category" : "shader"
        }

    def __init__(self):
        super().__init__("common/passthrough.vert", "post/chromaticaberration.frag")

    def set_uniforms(self, program):
        input_texture = self.input_texture
        input_texture.wrapping = gl.GL_MIRRORED_REPEAT
        for name in ("uRedOffset", "uGreenOffset", "uBlueOffset"):
            program[name] = self.get(name)

class HSVAdjust(Shader):
    class Meta:
        inputs = [
            {"name" : "uHue", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "uSaturation", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0, "range" : [0, float("inf")]}},
            {"name" : "uValue", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0, "range" : [0, float("inf")]}}
        ]
        outputs = [
        ]

    def __init__(self):
        super().__init__("common/passthrough.vert", "post/hsv_adjust.frag")

    def set_uniforms(self, program):
        input_texture = self.input_texture
        input_texture.wrapping = gl.GL_MIRRORED_REPEAT
        for name in ("uHue", "uSaturation", "uValue"):
            program[name] = self.get(name)

class GaussBlurPass(Shader):
    class Meta:
        inputs = [
            {"name" : "uSigma", "dtype" : dtype.float, "dtype_args" : {"default" : 3.0, "range" : [0.00001, float("inf")]}},
            {"name" : "uDirection", "dtype" : dtype.vec2, "dtype_args" : {"default" : np.float32([1, 0])}},
        ]
        options = {
            "virtual" : False,
            "category" : "shader"
        }

    def __init__(self):
        super().__init__("common/passthrough.vert", "post/gauss_blur.frag")

    def set_uniforms(self, program):
        input_texture = self.input_texture
        input_texture.wrapping = gl.GL_MIRRORED_REPEAT
        for name in ("uSigma", "uDirection"):
            program[name] = self.get(name)

class GaussBlur(Module):
    class Meta:
        pass

    def __init__(self):
        super().__init__("GaussBlur.json")

class Vignette(Shader):
    class Meta:
        inputs = [
            {"name" : "uRadius", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "uRadiusFactor", "dtype" : dtype.vec2, "dtype_args" : {"default" : np.float32([1.0, 1.0])}},
            {"name" : "uDistanceOrder", "dtype" : dtype.float, "dtype_args" : {"default" : 2.0, "range" : [0.0, float("inf")]}},
            {"name" : "uSoftness", "dtype" : dtype.float, "dtype_args" : {"default" : 0.35, "range" : [0.0, float("inf")]}},
            {"name" : "uIntensity", "dtype" : dtype.float, "dtype_args" : {"default" : 0.5, "range" : [0.0, 1.0]}},
        ]
        options = {
            "virtual" : False,
            "category" : "shader"
        }

    def __init__(self):
        super().__init__("common/passthrough.vert", "post/vignette.frag")

    def set_uniforms(self, program):
        for name in ("uRadius", "uRadiusFactor", "uDistanceOrder", "uSoftness", "uIntensity"):
            program[name] = self.get(name)

class MaskZoom(Shader):
    class Meta:
        inputs = [
            {"name" : "uMask", "dtype" : dtype.tex2d},
            {"name" : "uScale0", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "uScale1", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
        ]

    def __init__(self):
        super().__init__("common/passthrough.vert", "post/maskzoom.frag")

    def set_uniforms(self, program):
        for name in ("uMask", "uScale0", "uScale1"):
            program[name] = self.get(name)


