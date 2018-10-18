import math
import numpy as np
from pyvisual.node.base import Node
from pyvisual.node import dtype
from pyvisual.editor import widget
import imgui
from glumpy import gloo, gl, glm
from PIL import Image

class Render(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.tex2d, "widgets" : [widget.Texture]}
        ]
        outputs = []
        options = {
            "category" : "output",
        }


def checkerboard(grid_num=8, grid_size=32):
    row_even = grid_num // 2 * [0, 1]
    row_odd = grid_num // 2 * [1, 0]
    Z = np.row_stack(grid_num // 2 * (row_even, row_odd)).astype(np.uint8)
    return Z.repeat(grid_size, axis=0).repeat(grid_size, axis=1)

class Checkerboard(Node):
    class Meta:
        inputs = [
            {"name" : "test", "dtype" : dtype.float, "widgets" : [widget.Float]},
            {"name" : "c0", "dtype" : dtype.color, "widgets" : [widget.Color], "default" : np.float32([0.5, 0.0, 1.0, 1.0])}
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.tex2d, "widgets" : [widget.Texture]},
        ]
        options = {
            "category" : "input"
        }

    def __init__(self):
        super().__init__()
        self.texture = self.create_texture()

    def create_texture(self):
        data = np.zeros((8*32, 8*32, 4), dtype=np.float32)
        texture = data.view(gloo.Texture2D)
        texture.activate()
        texture.deactivate()
        return texture

    def populate_texture(self):
        c = checkerboard()
        self.texture[:, :] = self.get("c0")
        self.texture[:, :, 0] = np.multiply(self.texture[:, :, 0], c[:, :])
        self.texture[:, :, 1] = np.multiply(self.texture[:, :, 1], c[:, :])
        self.texture[:, :, 2] = np.multiply(self.texture[:, :, 2], c[:, :])
        # leave alpha
        #self.texture[:, :, 3] = np.multiply(self.texture[:, :, 3], c[:, :])
        self.texture.activate()
        self.texture.deactivate()

    def _evaluate(self):
        self.populate_texture()
        self.set("output", self.texture)

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

from pyvisual.rendering import util

class Shader(Node):
    class Meta:
        inputs = [
            {"name" : "enabled", "dtype" : dtype.bool, "widgets" : [widget.Bool], "default" : 1.0},
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

        vertex = util.load_shader(vertex)
        fragment = util.load_shader(fragment)
        self.quad = gloo.Program(vertex, fragment, version="130", count=4)
        self.quad["iPosition"] = [(-1,-1), (-1,+1), (+1,-1), (+1,+1)]
        self.quad["iTexCoord"] = [( 0, 1), ( 0, 0), ( 1, 1), ( 1, 0)]

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

        size = input_texture.shape[:2][::-1]
        fbo = self.get_fbo(size)
        fbo.activate()

        gl.glViewport(0, 0, size[0], size[1])
        gl.glClearColor(0.0, 0.0, 0.0, 0.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        # flip y-axis to get image right
        mvp = np.eye(4, dtype=np.float32)
        glm.scale(mvp, 1.0, -1.0, 1.0)
        self.quad["uModelViewProjection"] = mvp
        self.quad["uInputTexture"] = input_texture
        self.set_uniforms(self.quad)
        self.quad.draw(gl.GL_TRIANGLE_STRIP)

        fbo.deactivate()

        self.set("output", fbo.color[0])

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

class Translate(Node):
    class Meta:
        inputs = [
            {"name" : "x", "dtype" : dtype.float, "widgets" : [widget.Float]},
            {"name" : "y", "dtype" : dtype.float, "widgets" : [widget.Float]},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.mat3},
        ]

    def _evaluate(self):
        transform = np.array([[1.0, 0.0, self.get("x")],
                              [0.0, 1.0, self.get("y")],
                              [0.0, 0.0, 1.0]], dtype=np.float32)
        self.set("output", transform)

WRAPPING_MODES = ["repeat", "mirrored repeat", "clamp to edge", "clamp to border"]
WRAPPING_MODES_GL = [gl.GL_REPEAT, gl.GL_MIRRORED_REPEAT, gl.GL_CLAMP_TO_EDGE, gl.GL_CLAMP_TO_BORDER]
class SampleTexture(Shader):
    class Meta:
        inputs = [
            #{"name" : "direction", "dtype" : dtype.float, "widgets" : [widget.Float]},
            #{"name" : "distance", "dtype" : dtype.float, "widgets" : [widget.Float], "default" : 450.0},
            {"name" : "wrapping", "dtype" : dtype.int, "widgets" : [lambda node: widget.Choice(node, choices=WRAPPING_MODES)], "default" : 1},
            {"name" : "transform", "dtype" : dtype.mat3}
        ]
        options = {
            "virtual" : False,
            "category" : "shader"
        }

    def __init__(self):
        super().__init__("common/passthrough.vert", "post/move.frag")

    def set_uniforms(self, program):
        wrapping_mode = int(self.get("wrapping"))
        if wrapping_mode < 0 or wrapping_mode >= len(WRAPPING_MODES):
            wrapping_mode = 0
        input_texture = self.get("input")
        input_texture.wrapping = WRAPPING_MODES_GL[wrapping_mode]
        #program["uDirection"] = math.radians(self.get("direction"))
        #program["uDirectionOffset"] = self.get("distance")
        program["uTransform"] = self.get("transform")

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

dummy = np.zeros((1, 1, 4), dtype=np.uint8).view(gloo.Texture2D)
class Blend(Shader):
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
        super().__init__("common/passthrough.vert", "post/blend.frag")

    def set_uniforms(self, program):
        source = self.get("source")
        if source is None:
            program["uSource"] = dummy
            return
        program["uSource"] = source
        program["uAlpha"] = self.get("alpha")
