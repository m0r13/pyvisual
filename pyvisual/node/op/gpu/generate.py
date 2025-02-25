import os
import numpy as np
import urllib.request
import imgui
import clipboard
import json
import re
from pyvisual.node.op.gpu.base import BaseShader, Shader, ShaderNodeLoader
from pyvisual.node.op.module import StaticModule
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

empty_ssbo = np.array([0.0], dtype=np.float32).view(gloo.buffer.ShaderStorageBuffer)

class SSBOBars(Shader):
    class Meta:
        inputs = [
            {"name" : "ssbo", "dtype" : dtype.ssbo}
        ]

    def __init__(self):
        super().__init__("common/passthrough.vert", "generate/ssbo/SSBOBars.frag", handle_uniforms=True)

    def set_uniforms(self, program):
        super().set_uniforms(program)

        ssbo = self.get("ssbo")
        if ssbo is None:
            ssbo = empty_ssbo
        ssbo.activate()

        b = ssbo._handle
        gl.glBindBuffer(gl.GL_SHADER_STORAGE_BUFFER, b)
        gl.glBindBufferBase(gl.GL_SHADER_STORAGE_BUFFER, 0, b)

        program["uCount"] = len(ssbo)

class SSBOLines(Shader):
    class Meta:
        inputs = [
            {"name" : "ssbo", "dtype" : dtype.ssbo}
        ]

    def __init__(self):
        super().__init__("common/passthrough.vert", "generate/ssbo/SSBOLines.frag", handle_uniforms=True)

    def set_uniforms(self, program):
        super().set_uniforms(program)

        ssbo = self.get("ssbo")
        if ssbo is None:
            ssbo = empty_ssbo
        ssbo.activate()

        b = ssbo._handle
        gl.glBindBuffer(gl.GL_SHADER_STORAGE_BUFFER, b)
        gl.glBindBufferBase(gl.GL_SHADER_STORAGE_BUFFER, 0, b)

        program["uCount"] = len(ssbo)

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

        self._has_randomize_preset = "i_randomize_preset" in self.input_ports

    def _process_uniform_inputs(self, port_specs):
        # like in Filter class
        for port_spec in port_specs:
            if port_spec["name"] in ("time_mask", "time_d0", "time_d1"):
                port_spec["hide"] = not self.get("enable_time_mask")

    def _evaluate(self):
        if self.have_inputs_changed("enable_time_mask"):
            self.fragment_source.set("ENABLE_TIME_MASK", self.get("enable_time_mask"))

        if self._has_randomize_preset and self.get("randomize_preset"):
            self.randomize_preset(force=True)

        super()._evaluate()

class TimeMaskedGenerateWrapper(TimeMaskedGenerate):

    FRAGMENT = None

    def __init__(self):
        fragment_path = assets.get_shader_path(self.FRAGMENT)
        fragment_source = assets.FileShaderSource(fragment_path)
        super().__init__(fragment_source)

timemasked_loader = ShaderNodeLoader(
        wildcard="shader/generate/timemasked/*.frag", baseclass=TimeMaskedGenerateWrapper,
        module=__name__, globals_=globals()
)
raymarching_loader = ShaderNodeLoader(
        wildcard="shader/generate/timemasked/raymarching/*.frag", baseclass=TimeMaskedGenerateWrapper,
        module=__name__, globals_=globals()
)

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
#include <generate/timemasked/base.frag>
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
        # we store fragment source on our own
        # because it gets wrapped by another fragment source with define switches
        self._base_fragment_source = assets.StaticShaderSource()

        # it's possible to export the current shader and watch that file for changes
        # that way you can edit it and changes are loaded back
        self._reference_file_watcher = None

        super().__init__(self._base_fragment_source)

    def _export_fragment(self, path):
        f = open(path, "w")
        f.write(self.get("fragment_source"))
        f.close()

    def _set_fragment(self, source):
        # source is meant to be actual shader source code
        # which is not yet preprocessed
        self.get_input("fragment_source").value = source
        self._base_fragment_source.data = assets.load_shader(source=source)

    def _evaluate(self):
        # TODO this is a little hack
        # if fragment source gets loaded in first evaluation
        # id-input wouldn't be checked in elif
        # value wouldn't be created yet... only in next evaluation
        # and then it would count as changed
        # and (possibly modified) fragment source would be downloaded again / overwritten
        shader_id_changed = self.have_inputs_changed("id")

        if self._last_evaluated == 0.0:
            fragment_source = self.get("fragment_source")
            if fragment_source:
                self._set_fragment(fragment_source)
        elif shader_id_changed:
            shader_id = self.get("id")
            if shader_id:
                fragment_source = download_glslsandbox(shader_id)
                fragment_source = process_glslsandbox(fragment_source)
                self._set_fragment(fragment_source)
        elif self._reference_file_watcher is not None \
                and self._reference_file_watcher.has_changed():
            self._set_fragment(self._reference_file_watcher.read())

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
        if imgui.button("save fragment"):
            imgui.open_popup("save_fragment")
        base_path = os.path.join(assets.SHADER_PATH, "generate")
        save_path = node_widget.imgui_pick_file("save_fragment", base_path)
        if save_path is not None:
            self._export_fragment(save_path)

        imgui.same_line()
        if imgui.button("reference as file"):
            imgui.open_popup("reference_fragment")
        reference_path = node_widget.imgui_pick_file("reference_fragment", base_path)
        if reference_path is not None:
            self._export_fragment(reference_path)
            self._reference_file_watcher = assets.FileWatcher(reference_path)
