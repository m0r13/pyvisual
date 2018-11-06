import math
import numpy as np
import traceback
import random
import imgui
from pyvisual.node.base import Node
from pyvisual.node import dtype
from pyvisual.editor import widget
from pyvisual import assets
from glumpy import gloo, gl, glm
from PIL import Image

class RenderNode(Node):
    class Meta:
        options = {
            "virtual" : True
        }

    def __init__(self):
        super().__init__()

        self._fbo = None

    def get_fbo(self, size):
        if self._fbo is not None:
            h, w, _ = self._fbo.color[0].shape
            if size == (w, h):
                return self._fbo
        w, h = size
        texture = np.zeros((h, w, 4), dtype=np.uint8).view(gloo.Texture2D)
        self._fbo = gloo.FrameBuffer(color=[texture])
        return self._fbo

    def create_transform(self, m, texture_size, target_size):
        texture_aspect = texture_size[0] / texture_size[1]
        target_aspect = target_size[0] / target_size[1]

        model = np.eye(4, dtype=np.float32)
        view = np.eye(4, dtype=np.float32)
        projection = glm.ortho(-1.0, 1.0, -1.0, 1.0, -1.0, 1.0)
        texture = np.eye(4, dtype=np.float32)

        if abs(texture_aspect - target_aspect) < 0.001:
            pass
        elif texture_aspect < target_aspect:
            # border left/right
            glm.scale(model, texture_aspect, 1.0, 1.0)
            #glm.scale(projection, 1.0 / target_aspect, 1.0, 1.0)
            glm.scale(texture, target_aspect, 1.0, 1.0)
        else:
            # border top/bottom
            glm.scale(model, 1.0, 1.0 / texture_aspect, 1.0)
            #glm.scale(projection, 1.0, target_aspect, 1.0)
            glm.scale(texture, 1.0, 1.0 / target_aspect, 1.0)

        model = np.dot(model, m)

        glm.scale(model, 1.0, -1.0, 1.0)

        return model, view, projection, texture

    def render(self, size, render_func):
        fbo = self.get_fbo(size)
        fbo.activate()

        gl.glViewport(0, 0, size[0], size[1])
        gl.glClearColor(0.0, 0.0, 0.0, 0.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        render_func()

        fbo.deactivate()
        return fbo.color[0]

def load_shader(path):
    f = open(path, "r")
    data = f.read()
    f.close()
    return data

# TODO
dummy = np.zeros((1, 1, 4), dtype=np.uint8).view(gloo.Texture2D)
class Shader(RenderNode):
    class Meta:
        inputs = [
            {"name" : "enabled", "dtype" : dtype.bool, "dtype_args" : {"default" : 1.0}},
            {"name" : "transformUV", "dtype" : dtype.mat4},
            {"name" : "sizeref", "dtype" : dtype.tex2d},
            {"name" : "input", "dtype" : dtype.tex2d},
        ]
        outputs = [
            {"name" : "enabled", "dtype" : dtype.bool, "dtype_args" : {"default" : 1.0}},
            {"name" : "output", "dtype" : dtype.tex2d}
        ]
        options = {
            "virtual" : True
        }

    def __init__(self, vertex, fragment):
        super().__init__()

        self.vertex_watcher = assets.FileWatcher(assets.get_shader_path(vertex))
        self.fragment_watcher = assets.FileWatcher(assets.get_shader_path(fragment))
        self.update_program()

    def update_program(self):
        try:
            vertex = load_shader(self.vertex_watcher.path)
            fragment = load_shader(self.fragment_watcher.path)

            self.quad = gloo.Program(vertex, fragment, version="130", count=4)
            self.quad["iPosition"] = [(-1,-1), (-1,+1), (+1,-1), (+1,+1)]
            self.quad["iTexCoord"] = [( 0, 1), ( 0, 0), ( 1, 1), ( 1, 0)]

            # HACKY
            # we want to check if the built shader program compiles
            # need to run it once
            # but also set all uniform textures to dummy textures, otherwise it doesn't work
            # (that's how it's possible with glumpy at the moment)
            for uniform, gtype in self.quad.all_uniforms:
                if gtype == gl.GL_SAMPLER_2D:
                    self.quad[uniform] = dummy
            self.quad.draw(gl.GL_TRIANGLE_STRIP)

            self.shader_error = None
        except Exception as e:
            self.quad = None
            self.shader_error = traceback.format_exc()
            traceback.print_exc()

    def set_uniforms(self, program):
        pass

    def evaluate(self):
        if self.vertex_watcher.has_changed() or self.fragment_watcher.has_changed():
            self.update_program()

        return super().evaluate()

    def _evaluate(self):
        enabled = self.get("enabled")
        self.set("enabled", enabled)
        if not enabled or self.quad is None:
            self.set("output", self.get("input"))
            return

        input_texture = self.get("input")
        # TODO what to do?!
        if input_texture is None:
            self.set("output", None)
            return

        sizeref = self.get("sizeref")
        if sizeref is None:
            sizeref = input_texture
        texture_size = input_texture.shape[:2][::-1]
        target_size = sizeref.shape[:2][::-1]
        def do_render():
            custom_model = np.eye(4, dtype=np.float32)
            model, view, projection, texture = self.create_transform(custom_model, texture_size, target_size)
            self.quad["uModelViewProjection"] = np.dot(model, np.dot(view, projection))
            self.quad["uTextureSize"] = texture_size
            self.quad["uTransformUV"] = np.dot(texture, self.get("transformUV"))
            input_texture.interpolation = gl.GL_LINEAR
            input_texture.wrapping = gl.GL_CLAMP_TO_BORDER
            self.quad["uInputTexture"] = input_texture
            self.set_uniforms(self.quad)
            self.quad.draw(gl.GL_TRIANGLE_STRIP)

        self.set("output", self.render(target_size, do_render))

    def _show_custom_ui(self):
        if self.shader_error is None:
            return

        imgui.dummy(1, 5)
        imgui.text_colored("Shader error. (?)", 1.0, 0.0, 0.0)
        if imgui.is_item_hovered():
            imgui.set_tooltip(self.shader_error)

    def _show_custom_context(self):
        if imgui.menu_item("reload shaders")[0]:
            self.update_program()

class Blend(RenderNode):
    class Meta:
        inputs = [
            {"name" : "input1", "dtype" : dtype.tex2d},
            {"name" : "input2", "dtype" : dtype.tex2d},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.tex2d}
        ]
        options = {
            "virtual" : False
        }

    def __init__(self):
        super().__init__()

        vertex_path = assets.get_shader_path("common/passthrough.vert")
        fragment_path = assets.get_shader_path("common/passthrough.frag")

        vertex = load_shader(vertex_path)
        fragment = load_shader(fragment_path)
        self.quad = gloo.Program(vertex, fragment, version="130", count=4)
        self.quad["iPosition"] = [(-1,-1), (-1,+1), (+1,-1), (+1,+1)]
        self.quad["iTexCoord"] = [( 0, 1), ( 0, 0), ( 1, 1), ( 1, 0)]

    def set_uniforms(self, program):
        pass

    def _evaluate(self):
        input1 = self.get("input1")
        input2 = self.get("input2")
        if input1 is None:
            self.set("output", None)
            return

        if input2 is None:
            self.set("output", input1)
            return

        target_size = input1.shape[:2][::-1]
        input1_size = input1.shape[:2][::-1]
        input2_size = input2.shape[:2][::-1]
        def do_render():
            eye = np.eye(4, dtype=np.float32)

            model, view, projection, transform_uv = self.create_transform(eye, input1_size, target_size)
            self.quad["uModelViewProjection"] = np.dot(model, np.dot(view, projection))
            self.quad["uTextureSize"] = input1_size
            self.quad["uTransformUV"] = transform_uv
            self.quad["uInputTexture"] = input1
            self.quad.draw(gl.GL_TRIANGLE_STRIP)

            model, view, projection, transform_uv = self.create_transform(eye, input2_size, target_size)
            self.quad["uModelViewProjection"] = np.dot(model, np.dot(view, projection))
            self.quad["uTextureSize"] = input2_size
            self.quad["uTransformUV"] = transform_uv
            self.quad["uInputTexture"] = input2
            self.quad.draw(gl.GL_TRIANGLE_STRIP)

        self.set("output", self.render(target_size, do_render))


