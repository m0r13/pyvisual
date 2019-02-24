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

dummy = np.zeros((1, 1, 4), dtype=np.uint8).view(gloo.Texture2D)
class Mask(Shader):
    class Meta:
        inputs = [
            {"name" : "mask", "dtype" : dtype.tex2d},
        ]
        options = {
            "virtual" : False,
            "category" : "shader"
        }

    def __init__(self):
        super().__init__("common/passthrough.vert", "common/mask.frag")

    def set_uniforms(self, program):
        mask = self.get("mask")
        if mask is None:
            mask = dummy
        # TODO interpolation/wrapping?
        program["uMaskTexture"] = mask

class DualMask(Shader):
    class Meta:
        inputs = [
            #{"name" : "foreground", "dtype" : dtype.tex2d},
            #{"name" : "mask", "dtype" : dtype.tex2d},
        ]
        options = {
            "category" : "shader"
        }

    def __init__(self):
        super().__init__("common/passthrough.vert", "common/dual_mask.frag", handle_uniforms=True)

    #def set_uniforms(self, program):
    #    foreground = self.get("foreground")
    #    if foreground is None:
    #        foreground = dummy
    #    mask = self.get("mask")
    #    if mask is None:
    #        mask = dummy
    #    # TODO interpolation/wrapping?
    #    program["uInputTexture1"] = foreground
    #    program["uMaskTexture"] = mask

class MaskShadow(Shader):
    class Meta:
        inputs = [
            {"name" : "color", "dtype" : dtype.color, "dtype_args" : {"default" : np.array([0.8, 0.8, 0.8, 0.5])}},
            {"name" : "x", "dtype" : dtype.float, "dtype_args" : {"default" : 5.0}},
            {"name" : "y", "dtype" : dtype.float, "dtype_args" : {"default" : 5.0}},
        ]
        options = {
            "virtual" : False,
            "category" : "shader"
        }

    def __init__(self):
        super().__init__("common/passthrough.vert", "common/mask_shadow.frag")

    def set_uniforms(self, program):
        program["uColor"] = self.get("color")
        program["uOffset"] = [self.get("x"), self.get("y")]

