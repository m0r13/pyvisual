import math
import numpy as np
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
            {"name" : "path", "dtype" : dtype.assetpath, "widgets" : [lambda node: widget.AssetPath(node, "image/tartuvhs")]},
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
        print("load texture", self.get("path"))
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

        if texture_aspect < target_aspect:
            # border left/right
            glm.scale(model, texture_aspect, 1.0, 1.0)
            glm.scale(projection, 1.0 / target_aspect, 1.0, 1.0)
        else:
            # border top/bottom
            glm.scale(model, 1.0, 1.0 / texture_aspect, 1.0)
            glm.scale(projection, 1.0, target_aspect, 1.0)

        model = np.dot(model, m)

        glm.scale(model, 1.0, -1.0, 1.0)

        return model, view, projection

    def render(self, size, render_func):
        fbo = self.get_fbo(size)
        fbo.activate()

        gl.glViewport(0, 0, size[0], size[1])
        gl.glClearColor(0.0, 0.0, 0.0, 0.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        render_func()

        fbo.deactivate()
        return fbo.color[0]

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

        vertex = assets.load_shader(vertex)
        fragment = assets.load_shader(fragment)
        self.quad = gloo.Program(vertex, fragment, version="130", count=4)
        self.quad["iPosition"] = [(-1,-1), (-1,+1), (+1,-1), (+1,+1)]
        self.quad["iTexCoord"] = [( 0, 1), ( 0, 0), ( 1, 1), ( 1, 0)]

    def set_uniforms(self, program):
        pass

    def _evaluate(self):
        enabled = self.get("enabled")
        self.set("enabled", enabled)
        if not enabled:
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
            model, view, projection = self.create_transform(custom_model, texture_size, target_size)
            self.quad["uModelViewProjection"] = np.dot(model, np.dot(view, projection))
            self.quad["uTextureSize"] = texture_size
            self.quad["uTransformUV"] = self.get("transformUV")
            input_texture.interpolation = gl.GL_LINEAR
            input_texture.wrapping = gl.GL_CLAMP_TO_BORDER
            self.quad["uInputTexture"] = input_texture
            self.set_uniforms(self.quad)
            self.quad.draw(gl.GL_TRIANGLE_STRIP)

        self.set("output", self.render(target_size, do_render))

# TODO
dummy = np.zeros((1, 1, 4), dtype=np.uint8).view(gloo.Texture2D)
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

            model, view, projection = self.create_transform(eye, input1_size, target_size)
            self.quad["uModelViewProjection"] = np.dot(model, np.dot(view, projection))
            self.quad["uTextureSize"] = input1_size
            self.quad["uTransformUV"] = np.eye(4, dtype=np.float32)
            self.quad["uInputTexture"] = input1
            self.quad.draw(gl.GL_TRIANGLE_STRIP)

            model, view, projection = self.create_transform(eye, input2_size, target_size)
            self.quad["uModelViewProjection"] = np.dot(model, np.dot(view, projection))
            self.quad["uTextureSize"] = input2_size
            self.quad["uTransformUV"] = np.eye(4, dtype=np.float32)
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

class Mix(Shader):
    class Meta:
        inputs = [
            {"name" : "source", "dtype" : dtype.tex2d, "widgets" : [widget.Texture]},
            {"name" : "alpha", "dtype" : dtype.float, "widgets" : [lambda node: widget.Float(node, minmax=[0, 1])]},
        ]
        options = {
            "virtual" : False,
            "category" : "shader"
        }

    def __init__(self):
        super().__init__("common/passthrough.vert", "post/mix.frag")

    def set_uniforms(self, program):
        source = self.get("source")
        if source is None:
            program["uSource"] = dummy
            return
        program["uSource"] = source
        program["uAlpha"] = self.get("alpha")

