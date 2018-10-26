import os
import math
import numpy as np
import traceback
import random
from pyvisual.node.base import Node
from pyvisual.node import dtype
from pyvisual.editor import widget
from pyvisual import assets
import imgui
from glumpy import gloo, gl, glm
from PIL import Image

class LoadTexture(Node):
    class Meta:
        inputs = [
            {"name" : "path", "dtype" : dtype.assetpath, "widgets" : [lambda node: widget.AssetPath(node, "image")]},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.tex2d, "widgets" : [widget.Texture]},
        ]
        options = {
            "category" : "input"
        }

    def __init__(self):
        super().__init__()

        self.status = None

    def _evaluate(self):
        path = self.get("path")
        print("load texture", path)
        if not path:
            self.set("output", None)
            self.status = None
            return

        texture = None
        try:
            texture = np.array(Image.open(path)).view(gloo.Texture2D)
        except Exception as e:
            self.set("output", None)
            self.status = str(e)
            return

        texture.activate()
        texture.deactivate()
        self.status = None
        self.set("output", texture)

    def _show_custom_ui(self):
        if self.status:
            imgui.dummy(1, 5)
            imgui.text("Error. (?)")
            if imgui.is_item_hovered():
                imgui.set_tooltip(self.status)

class LoadMask(Node):
    class Meta:
        inputs = [
            {"name" : "path", "dtype" : dtype.assetpath, "widgets" : [lambda node: widget.AssetPath(node, "../data/image/mask")]},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.tex2d, "widgets" : [widget.Texture]},
        ]
        options = {
            "category" : "input"
        }

    def __init__(self):
        super().__init__()

        self.status = None

    def _evaluate(self):
        print("load mask", self.get("path"))
        texture = None
        try:
            texture = np.array(Image.open(self.get("path"))).view(gloo.Texture2D)
        except Exception as e:
            self.set("output", None)
            self.status = str(e)
            return

        texture.activate()
        texture.deactivate()
        self.status = None
        self.set("output", texture)

    def _show_custom_ui(self):
        if self.status:
            imgui.dummy(1, 5)
            imgui.text("Error. (?)")
            if imgui.is_item_hovered():
                imgui.set_tooltip(self.status)

class LoadTextures(Node):
    class Meta:
        inputs = [
            {"name" : "wildcard", "dtype" : dtype.assetpath, "widgets" : [lambda node: widget.AssetPath(node, "image")]},
            {"name" : "next", "dtype" : dtype.event, "widgets" : [widget.Button]},
            {"name" : "shuffle", "dtype" : dtype.bool, "widgets" : [widget.Bool], "default" : 1.0},
        ]
        outputs = [
            {"name" : "texture", "dtype" : dtype.tex2d, "widgets" : [widget.Texture]},
            {"name" : "last_texture", "dtype" : dtype.tex2d, "widgets" : [widget.Texture]},
            {"name" : "next", "dtype" : dtype.event, "widgets" : [widget.Button]},
        ]
        options = {
            "category" : "input"
        }

    def __init__(self):
        super().__init__()

        self.textures = []
        self.index = 0

        self.last_texture = None

    def _load_texture(self, path):
        texture = np.array(Image.open(path)).view(gloo.Texture2D)
        texture.activate()
        texture.deactivate()
        return texture

    def _evaluate(self):
        if self.have_inputs_changed("wildcard"):
            self.textures = []
            self.index = 0
            wildcard = self.get("wildcard")
            if wildcard:
                for path in assets.glob_paths(wildcard):
                    self.textures.append([os.path.join(assets.ASSET_PATH, path), None])

        if len(self.textures) == 0:
            self.set("texture", None)
            self.set("last_texture", None)
            return

        if self.get("next"):
            shuffle = self.get("shuffle")
            self.last_texture = self.textures[self.index][1]
            if shuffle and len(self.textures) > 1:
                self.index = (self.index + random.randint(1, len(self.textures) - 1)) % len(self.textures)
            else:
                self.index = (self.index + 1) % len(self.textures)
            print(self.index, self.textures[self.index][0])
        self.set("next", self.get("next"))

        tt = self.textures[self.index]
        if tt[1] is None:
            print("Loading %s" % tt[0])
            tt[1] = self._load_texture(tt[0])
        self.set("texture", tt[1])
        self.set("last_texture", self.last_texture)

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

# TODO
dummy = np.zeros((1, 1, 4), dtype=np.uint8).view(gloo.Texture2D)
class Shader(RenderNode):
    class Meta:
        inputs = [
            {"name" : "enabled", "dtype" : dtype.bool, "widgets" : [widget.Bool], "default" : 1.0},
            {"name" : "transformUV", "dtype" : dtype.mat4},
            {"name" : "sizeref", "dtype" : dtype.tex2d},
            {"name" : "input", "dtype" : dtype.tex2d, "widgets" : [widget.Texture]},
        ]
        outputs = [
            {"name" : "enabled", "dtype" : dtype.bool, "widgets" : [widget.Bool], "default" : 1.0},
            {"name" : "output", "dtype" : dtype.tex2d, "widgets" : [widget.Texture]}
        ]
        options = {
            "virtual" : True
        }

    def __init__(self, vertex, fragment):
        super().__init__()

        self.vertex = vertex
        self.fragment = fragment
        self.create_program()

    def create_program(self):
        # TODO also execute this automatically once shader has changed
        try:
            vertex = assets.load_shader(self.vertex)
            fragment = assets.load_shader(self.fragment)

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
            self.create_program()

class Mask(Shader):
    class Meta:
        inputs = [
            {"name" : "mask", "dtype" : dtype.tex2d, "widgets" : [widget.Texture]},
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
        program["uMaskTexture"] = mask

class Blend(RenderNode):
    class Meta:
        inputs = [
            {"name" : "input1", "dtype" : dtype.tex2d, "widgets" : [widget.Texture]},
            {"name" : "input2", "dtype" : dtype.tex2d, "widgets" : [widget.Texture]},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.tex2d, "widgets" : [widget.Texture]}
        ]
        options = {
            "virtual" : False
        }

    def __init__(self):
        super().__init__()

        vertex = "common/passthrough.vert"
        fragment = "common/passthrough.frag"

        vertex = assets.load_shader(vertex)
        fragment = assets.load_shader(fragment)
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

class Glitch(Shader):
    class Meta:
        inputs = [
            #{"name" : "mode", "dtype" : dtype.int, "widgets" : [lambda node: widget.Choice(node, choices=["0", "1", "2"])]},
            {"name" : "time", "dtype" : dtype.float, "widgets" : [widget.Float]},
            {"name" : "amount", "dtype" : dtype.float, "widgets" : [widget.Float]},
            {"name" : "speed", "dtype" : dtype.float, "widgets" : [widget.Float]},
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
class SampleTexture(Shader):
    class Meta:
        inputs = [
            {"name" : "wrapping", "dtype" : dtype.int, "widgets" : [lambda node: widget.Choice(node, choices=WRAPPING_MODES)], "default" : 1},
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
        input_texture = self.get("input")
        input_texture.wrapping = WRAPPING_MODES_GL[wrapping_mode]

class Mirror(Shader):
    class Meta:
        inputs = [
            {"name" : "mode", "dtype" : dtype.int, "widgets" : [lambda node: widget.Int(node, minmax=[0, 3])]},
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
            {"name" : "axis_angle", "dtype" : dtype.float, "widgets" : [widget.Float], "default" : 0.0},
            {"name" : "angle", "dtype" : dtype.float, "widgets" : [widget.Float], "default" : 0.0},
            {"name" : "segments", "dtype" : dtype.int, "widgets" : [widget.Int], "default" : 5.0},
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

class MaskShadow(Shader):
    class Meta:
        inputs = [
            {"name" : "color", "dtype" : dtype.color, "widgets" : [widget.Color], "default" : np.array([0.8, 0.8, 0.8, 0.5])},
            {"name" : "x", "dtype" : dtype.float, "widgets" : [widget.Float], "default" : 5.0},
            {"name" : "y", "dtype" : dtype.float, "widgets" : [widget.Float], "default" : 5.0},
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

class MixTexture(Shader):
    class Meta:
        inputs = [
            {"name" : "destination", "dtype" : dtype.tex2d, "widgets" : [widget.Texture]},
            {"name" : "alpha", "dtype" : dtype.float, "widgets" : [lambda node: widget.Float(node, minmax=[0, 1])]},
        ]
        options = {
            "virtual" : True,
            "category" : "shader"
        }

    def set_uniforms(self, program):
        source = self.get("destination")
        if source is None:
            program["uDestinationTexture"] = dummy
            return
        program["uDestinationTexture"] = source
        program["uAlpha"] = self.get("alpha")

class LerpMixTexture(MixTexture):
    class Meta:
        options = {
            "virtual" : False,
            "category" : "shader"
        }

    def __init__(self):
        super().__init__("common/passthrough.vert", "transition/lerp.frag")

class MoveMixTexture(MixTexture):
    class Meta:
        inputs = [
            {"name" : "x", "dtype" : dtype.float, "widgets" : [widget.Float], "default" : 1.0},
            {"name" : "y", "dtype" : dtype.float, "widgets" : [widget.Float], "default" : 1.0},
        ]
        options = {
            "virtual" : False,
            "category" : "shader"
        }

    def __init__(self):
        super().__init__("common/passthrough.vert", "transition/move.frag")

    def set_uniforms(self, program):
        super().set_uniforms(program)

        program["uDirection"] = (self.get("x"), self.get("y"))

class SwipeMixTexture(MixTexture):
    class Meta:
        inputs = [
            {"name" : "x", "dtype" : dtype.float, "widgets" : [widget.Float], "default" : 1.0},
            {"name" : "y", "dtype" : dtype.float, "widgets" : [widget.Float], "default" : 1.0},
        ]
        options = {
            "virtual" : False,
            "category" : "shader"
        }

    def __init__(self):
        super().__init__("common/passthrough.vert", "transition/swipe.frag")

    def set_uniforms(self, program):
        super().set_uniforms(program)

        program["uDirection"] = (self.get("x"), self.get("y"))

# TODO node restructuring
from pyvisual.node.generate import scalable_timer
class TransitionTimer(Node):
    class Meta:
        inputs = [
            {"name" : "duration", "dtype" : dtype.float, "widgets" : [widget.Float], "default" : 1.0},
            {"name" : "trigger", "dtype" : dtype.event, "widgets" : [widget.Button]},
            {"name" : "reverse", "dtype" : dtype.bool, "widgets" : [widget.Bool], "default" : 1.0},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float, "widgets" : [widget.Float]},
        ]

    def __init__(self):
        super().__init__()

        self.time = scalable_timer()

    def _evaluate(self):
        duration = self.get("duration")
        scale = float("inf") if duration == 0.0 else 1.0 / duration
        t = 0.0
        if self.get("reverse"):
            t = max(0.0, 1.0 - self.time(scale, self.get("trigger")))
        else:
            t = min(1.0, self.time(scale, self.get("trigger")))
        self.set("output", t)

