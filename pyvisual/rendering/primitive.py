import logging
from glumpy import gloo, gl
import numpy as np
from . import util

log = logging.getLogger(__name__)

class Primitive(gloo.Program):
    def __init__(self, vertex, fragment, *args, **kwargs):
        super().__init__(util.load_shader(vertex), util.load_shader(fragment), version="130", *args, **kwargs)

        log.debug("Creating program %s %s" % (vertex, fragment))

class TextureQuad(Primitive):
    def __init__(self, vertex, fragment):
        super().__init__(vertex, fragment, count=4)
        self["iPosition"] = [(-1,-1), (-1,+1), (+1,-1), (+1,+1)]
        self["iTexCoord"] = [( 0, 1), ( 0, 0), ( 1, 1), ( 1, 0)]

    def render(self, texture, transformation):
        self["uModelViewProjection"] = transformation
        self["uInputTexture"] = texture
        self.draw(gl.GL_TRIANGLE_STRIP)

class ColorQuad(Primitive):
    def __init__(self):
        super().__init__("common/passthrough.vert", "common/color.frag", count=4)

    def render(self, rect, color, transformation):
        x0, y0, x1, y1 = rect
        points = [(x0, y0), (x0, y1), (x1, y0), (x1, y1)]

        self["iPosition"] = points
        self["uModelViewProjection"] = transformation
        self["uColor"] = color
        self.draw(gl.GL_TRIANGLE_STRIP)

class Lines(Primitive):
    def __init__(self, num_points):
        super().__init__("common/passthrough.vert", "common/color.frag", count=num_points)

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

def draw_line(p0, p1, color, transformation):
    points = [p0, p1]
    draw_lines(points, color, transformation)

def draw_rect(x0, y0, x1, y1, color, transformation):
    points = [(x0, y0), (x0, y1), (x1, y1), (x1, y0)]
    draw_lines(points, color, transformation, loop=True)

color_quad = None
def fill_rect(rect, color, transformation):
    global color_quad
    if color_quad is None:
        color_quad = ColorQuad()
    #quad = ColorQuad()
    color_quad.render(rect, color, transformation)
