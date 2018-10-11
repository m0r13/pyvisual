import numpy as np
from pyvisual.node.base import Node
from pyvisual.node import dtype
from pyvisual.editor import widget
from glumpy import gloo

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

class DummyTexture(Node):
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

class InputTexture(Node):
    class Meta:
        outputs = [
            {"name" : "output", "dtype" : dtype.tex2d, "widgets" : [widget.Texture]},
        ]
        options = {
            "category" : "input"
        }

