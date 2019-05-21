import math
import os
import numpy as np
import traceback
import random
import imgui
from pyvisual.node.base import Node
from pyvisual.node.op.gpu.base import BaseShader, Shader, ShaderNodeLoader
from pyvisual.node.op.module import StaticModule
from pyvisual.node import dtype
from pyvisual.editor import widget
from pyvisual import assets
from glumpy import gloo, gl, glm
from PIL import Image

class Filter(BaseShader):
    class Meta:
        inputs = [
            {"name" : "advanced_filtering", "dtype" : dtype.bool, "dtype_args" : {"default" : False}, "group" : "additional"},
        ]

        options = {
            "virtual" : True
        }

    def __init__(self, vertex_path, fragment_path):
        vertex_path = assets.get_shader_path(vertex_path)
        fragment_path = assets.get_shader_path(fragment_path)

        vertex_source = assets.FileShaderSource(vertex_path)
        fragment_source = assets.CustomDefineShaderSource(assets.FileShaderSource(fragment_path))
        # just to have the default define values here
        fragment_source.set("ADVANCED_FILTERING", False)

        super().__init__(vertex_source, fragment_source, handle_uniforms=True)

        self._has_randomize_preset = "i_randomize_preset" in self.input_ports

    def _process_uniform_inputs(self, port_specs):
        # called by Shader class when custom node inputs for uniforms are created
        # show advanced filter related inputs only when advanced filtering is enabled
        for port_spec in port_specs:
            if port_spec["name"] in ("filter_mask", "mask_factor", "mask_invert", "filter_mode", "filter_bg"):
                port_spec["hide"] = not self.get("advanced_filtering")

    def _evaluate(self):
        if self.have_inputs_changed("advanced_filtering"):
            self.fragment_source.set("ADVANCED_FILTERING", self.get("advanced_filtering"))

        if self._has_randomize_preset and self.get("randomize_preset"):
            self.randomize_preset(force=True)

        super()._evaluate()

class FilterWrapper(Filter):
    class Meta:
        options = {
            "virtual" : True
        }

    VERTEX = "common/passthrough.vert"
    FRAGMENT = "filter/passthrough.frag"

    def __init__(self):
        super().__init__(self.VERTEX, self.FRAGMENT)

filter_loader = ShaderNodeLoader(
        wildcard="shader/filter/*.frag", baseclass=FilterWrapper,
        module=__name__, globals_=globals()
)

class GaussBlur(StaticModule):
    class Meta:
        options = {
            "virtual" : False
        }

    def __init__(self):
        super().__init__("GaussBlur.json")

