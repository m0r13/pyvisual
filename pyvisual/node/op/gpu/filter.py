import math
import os
import numpy as np
import traceback
import random
import imgui
from pyvisual.node.base import Node
from pyvisual.node.op.gpu.base import BaseShader, Shader
from pyvisual.node.op.module import Module
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

    def __init__(self, vertex_path, fragment_path):
        vertex_path = assets.get_shader_path(vertex_path)
        fragment_path = assets.get_shader_path(fragment_path)

        vertex_source = assets.FileShaderSource(vertex_path)
        fragment_source = assets.CustomDefineShaderSource(assets.FileShaderSource(fragment_path))
        # just to have the default define values here
        fragment_source.set("ADVANCED_FILTERING", False)

        super().__init__(vertex_source, fragment_source, handle_uniforms=True)

    def _process_uniform_inputs(self, port_specs):
        # called by Shader class when custom node inputs for uniforms are created
        # show advanced filter related inputs only when advanced filtering is enabled
        for port_spec in port_specs:
            if port_spec["name"] in ("filter_mask", "filter_mode", "filter_bg"):
                port_spec["hide"] = not self.get("advanced_filtering")

    def _evaluate(self):
        if self.have_inputs_changed("advanced_filtering"):
            self.fragment_source.set("ADVANCED_FILTERING", self.get("advanced_filtering"))

        super()._evaluate()

class GeneratedFilterMeta:
    options = {
        "virtual" : False
    }

class GeneratedFilter(Filter):
    class Meta:
        options = {
            "virtual" : True
        }

    VERTEX = "common/passthrough.vert"
    FRAGMENT = "filter/passthrough.frag"

    def __init__(self):
        super().__init__(self.VERTEX, self.FRAGMENT)

def load_filter_classes():
    module = __name__
    g = globals()
    for path in assets.glob_paths("shader/filter/*.frag"):
        name = os.path.basename(path).replace(".frag", "")
        if name == "basefilter":
            continue
        if name in g:
            if isinstance(g[name], GeneratedFilter):
                print("### Warning: Seems that filter class name %s in module %s is already" % (name, module))
            else:
                # filter class already exist, no need to recreate it for now
                continue
        fragment_path = path.replace("shader" + os.path.sep, "")
        attrs = {"FRAGMENT" : fragment_path, "Meta" : GeneratedFilterMeta, "__module__" : module}
        filter_class = type(name, (GeneratedFilter,), attrs)
        g[name] = filter_class
        del filter_class

load_filter_classes()

class GaussBlur(Module):
    class Meta:
        pass

    def __init__(self):
        super().__init__("GaussBlur.json")

