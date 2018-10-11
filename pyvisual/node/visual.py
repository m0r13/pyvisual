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
    return 255 * Z.repeat(grid_size, axis=0).repeat(grid_size, axis=1)

class DummyTexture(Node):
    class Meta:
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
        grid_num = 8
        grid_size = 32

        data = np.zeros((8*32, 8*32, 4), dtype=np.uint8)
        data[:, :] = [128, 0, 255, 255]
        data = checkerboard()
        texture = data.view(gloo.Texture2D)
        texture.activate()
        return texture

    def evaluate(self):
        self.set("output", self.texture)

class InputTexture(Node):
    class Meta:
        outputs = [
            {"name" : "output", "dtype" : dtype.tex2d, "widgets" : [widget.Texture]},
        ]
        options = {
            "category" : "input"
        }

