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
uniform sampler2D uInputTexture; // {"skip" : true}
uniform float uTime; // {"alias" : "time"}

in vec2 TexCoord0;
out vec4 oFragColor;

"""

MAIN = """

void main() {
    resolution = textureSize(uInputTexture, 0).xy;
"""

def process_glslsandbox(source):
    match = re.search("void\s+main\s*\(\s*(\s*void\s*)?\)\s*\{", source)
    if match is None:
        print(source)
        assert False
    main = match.group()

    source = source.replace("uniform float time;", "")
    source = source.replace("time", "uTime")
    source = source.replace("uniform vec2 resolution", "vec2 resolution")
    source = source.replace("mediump", "highp")
    source = source.replace("#extension", "//#extension")
    source = source.replace(main, MAIN)
    source = source.replace("gl_FragCoord", "(vec2(TexCoord0.x, 1.0 - TexCoord0.y) * resolution)")
    source = source.replace("gl_FragColor", "oFragColor")
    # add this at last because I don't want to replace anything
    # in the header part (like "time")
    source = BEGIN + source

    return source

class GLSLSandbox(BaseShader):
    class Meta:
        inputs = [
            {"name" : "id", "dtype" : dtype.str, "group" : "additional"},
            {"name" : "fragment_source", "dtype" : dtype.str, "hide" : True},
        ]

    def __init__(self):
        vertex_path = assets.get_shader_path("common/passthrough.vert")
        vertex_source = assets.FileShaderSource(vertex_path)
        fragment_source = assets.StaticShaderSource()

        super().__init__(vertex_source, fragment_source, handle_uniforms=True)

    def _evaluate(self):
        if self._last_evaluated == 0.0:
            fragment_source = self.get("fragment_source")
            if fragment_source:
                self.fragment_source.data = fragment_source

        if self.have_inputs_changed("id"):
            shader_id = self.get("id")
            if shader_id:
                fragment_source = download_glslsandbox(shader_id)
                fragment_source = process_glslsandbox(fragment_source)
                self.get_input("fragment_source").value = fragment_source
                self.fragment_source.data = fragment_source

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
            f.write(self.fragment_source.data)
            f.close()

