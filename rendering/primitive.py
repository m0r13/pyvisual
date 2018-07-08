from glumpy import gloo, gl
import numpy as np
from . import util

class TextureQuad(gloo.Program):
    def __init__(self, vertex, fragment):
        super().__init__(util.load_shader(vertex), util.load_shader(fragment), count=4, version="130")
        self["iPosition"] = [(-1,-1), (-1,+1), (+1,-1), (+1,+1)]
        self["iTexCoord"] = [( 0, 1), ( 0, 0), ( 1, 1), ( 1, 0)]

    def render(self, texture, transformation):
        self["uModelViewProjection"] = transformation
        self["uInputTexture"] = texture
        self.draw(gl.GL_TRIANGLE_STRIP)

class Lines(gloo.Program):
    def __init__(self, num_points):
        super().__init__(util.load_shader("common/passthrough.vert"), util.load_shader("common/color.frag"), count=num_points, version="130")

    def render(self, points, color, transformation):
        self["iPosition"] = points
        self["uModelViewProjection"] = transformation
        self["uColor"] = color
        self.draw(gl.GL_LINE_STRIP)

def draw_lines(points, color, transformation, loop=False):
    if loop:
        points = points + [points[0]]
    lines = Lines(len(points))
    lines.render(points, color, transformation)

def draw_line(x0, y0, x1, y1, color, transformation):
    points = [(x0, y0), (x1, y1)]
    draw_lines(points, color, transformation)

def draw_rect(x0, y0, x1, y1, color, transformation):
    points = [(x0, y0), (x0, y1), (x1, y1), (x1, y0)]
    draw_lines(points, color, transformation, loop=True)
