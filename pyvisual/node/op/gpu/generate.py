import os
import numpy as np
import urllib.request
import imgui
import clipboard
import json
import re
from pyvisual.node.op.gpu.base import BaseShader, Shader
from pyvisual.node import dtype
import pyvisual.editor.widget as node_widget
from pyvisual import assets
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

class TimeMaskedGenerate(BaseShader):
    class Meta:
        inputs = [
            {"name" : "enable_time_mask", "dtype" : dtype.bool, "dtype_args" : {"default" : False}, "group" : "additional"},
        ]
        options = {
            "virtual" : True
        }

    def __init__(self, fragment_source):
        vertex_path = assets.get_shader_path("common/passthrough.vert")
        vertex_source = assets.FileShaderSource(vertex_path)
        fragment_source = assets.CustomDefineShaderSource(fragment_source)
        fragment_source.set("ENABLE_TIME_MASK", False)

        super().__init__(vertex_source, fragment_source, handle_uniforms=True)

    def _process_uniform_inputs(self, port_specs):
        # like in Filter class
        for port_spec in port_specs:
            if port_spec["name"] in ("time_mask", "time_d0", "time_d1"):
                port_spec["hide"] = not self.get("enable_time_mask")

    def _evaluate(self):
        if self.have_inputs_changed("enable_time_mask"):
            self.fragment_source.set("ENABLE_TIME_MASK", self.get("enable_time_mask"))

        super()._evaluate()

def download_glslsandbox(shader_id):
    assert shader_id is not None
    url = "http://glslsandbox.com/item/%s" % shader_id
    response = urllib.request.urlopen(url)
    data = json.loads(response.read())
    if not "code" in data:
        return None
    header_url = "http://glslsandbox.com/e#%s" % shader_id
    header = "// Shader downloaded and adapted from glslsandbox.com\n// URL: %s\n\n" % header_url
    code = header + data["code"]
    return code

BEGIN = """
#include <generate/base_time_mask.frag>
"""

MAIN = """

void generateFrag() {

"""

def process_glslsandbox(source):
    match = re.search("void\s+main\s*\(\s*(\s*void\s*)?\)\s*\{", source)
    if match is None:
        print(source)
        assert False
    main = match.group()

    source = source.replace("uniform float time;", "")
    source = source.replace("time", "pyvisualTime")
    #source = source.replace("uv", "pyvisualUV")
    source = source.replace("uniform vec2 resolution", "")
    #source = source.replace("mediump", "highp")
    source = source.replace("#extension", "//#extension")
    source = source.replace(main, MAIN)
    source = source.replace("resolution", "pyvisualResolution")
    source = source.replace("gl_FragCoord", "(vec2(pyvisualUV.x, 1.0 - pyvisualUV.y) * pyvisualResolution)")
    source = source.replace("gl_FragColor", "pyvisualOutColor")
    # add this at last because I don't want to replace anything
    # in the header part (like "time")
    source = BEGIN + source

    return source

class GLSLSandbox(TimeMaskedGenerate):
    class Meta:
        inputs = [
            {"name" : "id", "dtype" : dtype.str, "group" : "additional"},
            {"name" : "fragment_source", "dtype" : dtype.str, "hide" : True},
        ]

    def __init__(self):
        # we have to store it additionally
        # because it gets wrapped by a fragment source with define switches
        self._glsl_fragment_source = assets.StaticShaderSource()
        super().__init__(self._glsl_fragment_source)

    def _evaluate(self):
        if self._last_evaluated == 0.0:
            fragment_source = self.get("fragment_source")
            if fragment_source:
                self._glsl_fragment_source.data = assets.load_shader(source=fragment_source)
        elif self.have_inputs_changed("id"):
            shader_id = self.get("id")
            if shader_id:
                fragment_source = download_glslsandbox(shader_id)
                fragment_source = process_glslsandbox(fragment_source)
                self.get_input("fragment_source").value = fragment_source
                # assets.load_shader is important!
                # preprocesses includes etc.
                # also we don't want preprocessed includes in the stored fragment sources
                self._glsl_fragment_source.data = assets.load_shader(source=fragment_source)

        super()._evaluate()

    def _show_custom_context(self):
        if imgui.button("paste url"):
            shader_id = clipboard.paste().strip()
            if shader_id.startswith("http://glslsandbox.com/e#"):
                shader_id = shader_id.replace("http://glslsandbox.com/e#", "")
            self.get_input("id").value = shader_id

        imgui.same_line()
        if imgui.button("copy url"):
            shader_id = self.get("id")
            url = "http://glslsandbox.com/e#%s" % shader_id
            clipboard.copy(url)

        imgui.same_line()
        if imgui.button("save fragment shader"):
            imgui.open_popup("save_fragment")

        base_path = os.path.join(assets.SHADER_PATH, "generate")
        path = node_widget.imgui_pick_file("save_fragment", base_path)
        if path is not None:
            f = open(path, "w")
            f.write(self.get("fragment_source"))
            f.close()

