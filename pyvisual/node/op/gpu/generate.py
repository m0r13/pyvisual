import numpy as np
from pyvisual.node.op.gpu.base import Shader
from pyvisual.node import dtype
from glumpy import gloo, gl, glm

# TODO
# a problem with shaders without proper input texture is that
# they are rendered to size of sizeref texture, but uInputTexture doesn't have that size
# i.e. textureSize(...) as usually used returns wrong result

class Fill(Shader):
    class Meta:
        inputs = [
            {"name" : "uColor", "dtype" : dtype.color, "dtype_args" : {"default" : np.float32([1.0, 1.0, 1.0, 1.0])}},
        ]

    def __init__(self):
        super().__init__("common/passthrough.vert", "generate/fill.frag")

    def set_uniforms(self, program):
        program["uColor"] = self.get("uColor")

class Noise(Shader):
    class Meta:
        inputs = [
            {"name" : "uTransform", "dtype" : dtype.mat4},
            {"name" : "uValueFactor", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "uValueOffset", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "uValueThreshold", "dtype" : dtype.float, "dtype_args" : {"default" : 0.5}},
            {"name" : "uValueSoftness", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "uTime", "dtype" : dtype.float},
        ]

    def __init__(self):
        super().__init__("common/passthrough.vert", "generate/noise3D.frag")

    def set_uniforms(self, program):
        program["uTransform"] = self.get("uTransform")
        program["uValueFactor"] = self.get("uValueFactor")
        program["uValueOffset"] = self.get("uValueOffset")
        program["uValueThreshold"] = self.get("uValueThreshold")
        program["uValueSoftness"] = self.get("uValueSoftness")
        program["uTime"] = self.get("uTime")

class Wolfenstein(Shader):
    class Meta:
        inputs = [
            {"name" : "uTime", "dtype" : dtype.float},
        ]

    def __init__(self):
        super().__init__("common/passthrough.vert", "generate/wolfenstein.frag")

    def set_uniforms(self, program):
        program["uTime"] = self.get("uTime")

