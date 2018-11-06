import os
import numpy as np
import random
from pyvisual.node.base import Node
from pyvisual.node import dtype
from pyvisual import assets
import imgui
from glumpy import gloo, gl, glm
from PIL import Image

class LoadTexture(Node):
    class Meta:
        inputs = [
            {"name" : "path", "dtype" : dtype.assetpath, "dtype_args" : {"prefix" : "image"}},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.tex2d},
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
            texture = np.array(Image.open(os.path.join(assets.ASSET_PATH, path))).view(gloo.Texture2D)
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
            imgui.text_colored("Error. (?)", 1.0, 0.0, 0.0)
            if imgui.is_item_hovered():
                imgui.set_tooltip(self.status)

class LoadTextures(Node):
    class Meta:
        inputs = [
            {"name" : "wildcard", "dtype" : dtype.assetpath, "dtype_args" : {"prefix" : "image"}},
            {"name" : "next", "dtype" : dtype.event},
            {"name" : "shuffle", "dtype" : dtype.bool, "dtype_args" : {"default" : 1.0}},
        ]
        outputs = [
            {"name" : "texture", "dtype" : dtype.tex2d},
            {"name" : "last_texture", "dtype" : dtype.tex2d},
            {"name" : "next", "dtype" : dtype.event},
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

class Renderer(Node):
    class Meta:
        inputs = [
            {"name" : "texture", "dtype" : dtype.tex2d}
        ]

    def __init__(self):
        super().__init__()

        self.texture = None

    def _evaluate(self):
        self.texture = self.get("texture")
