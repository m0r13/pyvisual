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
            data = np.array(Image.open(os.path.join(assets.ASSET_PATH, path)))
            texture = data.view(gloo.Texture2D)
            self.status = None
        except Exception as e:
            self.set("output", None)
            self.status = str(e)
            return

        texture.activate()
        texture.deactivate()
        self.set("output", texture)

    def _show_custom_ui(self):
        if self.status:
            imgui.dummy(1, 5)
            imgui.text_colored("Error. (?)", 1.0, 0.0, 0.0)
            if imgui.is_item_hovered():
                imgui.set_tooltip(self.status)

    def _show_custom_context(self):
        if imgui.button("Reload texture"):
            self.force_evaluate()

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
        initial_state = {
            "index" : 0
        }
        random_state = {
            "index" : lambda node: random.randint(0, 10000)
        }

    def __init__(self):
        super().__init__()

        # available textures as tuples (path, glumpy-texture)
        # glumpy-textures are None until loaded for the first time
        self.textures = []
        # index is set by state
        #self.index = 0

        self.last_texture = None

    def _load_texture(self, path):
        texture = np.array(Image.open(os.path.join(assets.ASSET_PATH, path))).view(gloo.Texture2D)
        texture.activate()
        texture.deactivate()
        return texture

    # TODO refactor whole mechanism of choosing texture together with state!
    def _set_index(self, index):
        self.index = index % len(self.textures)

        tt = self.textures[self.index]
        if tt[1] is None:
            print("Loading %s" % tt[0])
            tt[1] = self._load_texture(tt[0])
        self.set("texture", tt[1])
        self.set("last_texture", self.last_texture)

    def _evaluate(self):
        if self.have_inputs_changed("wildcard"):
            self.textures = []
            wildcard = self.get("wildcard")
            if wildcard:
                for i, path in enumerate(sorted(assets.glob_paths(wildcard))):
                    self.textures.append([path, None])

        if len(self.textures) == 0:
            self.set("texture", None)
            self.set("last_texture", None)
            return

        self.set("next", self.get("next"))
        if self.get("next"):
            shuffle = self.get("shuffle")
            self.last_texture = self.textures[self.index][1]
            if shuffle and len(self.textures) > 1:
                index = (self.index + random.randint(1, len(self.textures) - 1)) % len(self.textures)
            else:
                index = (self.index + 1) % len(self.textures)

            self.index = index

        self._set_index(self.index)

    def get_state(self):
        return {"index" : self.index}

    def set_state(self, state):
        if "index" in state:
            self.index = state["index"]

class DummyTexture(Node):
    class Meta:
        inputs = [
            {"name" : "aspect", "dtype" : dtype.str, "dtype_args" : {"default" : "16:9"}},
            {"name" : "height", "dtype" : dtype.int, "dtype_args" : {"default" : 1080}},
        ]
        outputs = [
            {"name" : "out", "dtype" : dtype.tex2d}
        ]

    def __init__(self):
        super().__init__()

        self._texture = None

    def _evaluate(self):
        if self._texture is not None:
            self._texture.delete()

        aspect = self.get("aspect").strip()
        parts = aspect.split(":")
        try:
            aspect_w, aspect_h = float(parts[0]), float(parts[1])
        except (IndexError, ValueError):
            return

        a = aspect_w / aspect_h
        height = int(self.get("height"))
        width = int(a * height)

        self._texture = np.zeros((height, width, 1), dtype=np.uint8).view(gloo.Texture2D)
        self.set("out", self._texture)

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

class ChooseTexture(Node):
    class Meta:
        inputs = [
            {"name" : "count", "dtype" : dtype.int, "dtype_args" : {"default" : 2, "range" : [0, float("inf")]}, "group" : "additional"},
            {"name" : "index", "dtype" : dtype.int, "dtype_args" : {"default" : 0, "range" : [-1, float("inf")]}},
            {"name" : "next", "dtype" : dtype.event},
            {"name" : "randomize", "dtype" : dtype.event},
        ]
        outputs = [
            {"name" : "out", "dtype" : dtype.tex2d},
            {"name" : "dummy0", "dtype" : dtype.int, "dummy" : True},
            {"name" : "dummy1", "dtype" : dtype.int, "dummy" : True},
        ]
        initial_state = {
            "index" : 0
        }
        # TODO refactor state handling here too!!!!
        random_state = {
            "index" : lambda node: random.randint(0, 10000)
        }

    def __init__(self):
        self._count = None

        super().__init__()

        # keep current index and next index
        # when a new texture should be choosen, next index is choosen randomly and that enable flag is set
        # only in the next frame that texture is delegated and set as current
        # (to prevent weird glitches when a generator is not enabled yet)
        self._current_index = -1
        # set by state
        #self._next_index = -1

    def _set_next(self, index):
        self._next_index = index % self._count

        self.get_input("index").value = self._next_index
        self.get_output("enabled%d" % self._next_index).value = True

    def _update_custom_ports(self):
        self._count = int(self.get("count"))

        custom_inputs = []
        custom_outputs = []
        for i in range(self._count):
            input_port = {"name" : "in%d" % i, "dtype" : dtype.tex2d}
            output_port = {"name" : "enabled%d" % i, "dtype" : dtype.bool}
            custom_inputs.append(input_port)
            custom_outputs.append(output_port)
        self.set_custom_inputs(custom_inputs)
        self.set_custom_outputs(custom_outputs)

        if (self._current_index >= self._count or self._current_index == -1) and self._next_index == -1:
            self._set_next(0)

    def _evaluate(self):
        if self.have_inputs_changed("count") or self._last_evaluated == 0.0:
            self._update_custom_ports()

        if self._next_index != -1:
            self._current_index = self._next_index % self._count
            self._next_index = -1

            # update all enabled-flags, necessary after choosing new texture
            iterator = zip(self.yield_custom_input_values(), self.yield_custom_output_values())
            for i, ((_0, in_texture), (_1, out_enabled)) in enumerate(iterator):
                enabled = i == self._current_index
                out_enabled.value = enabled
                if enabled:
                    self.set("out", in_texture.value)

        if self.have_inputs_changed("index"):
            self.set_state({"index" : self.get("index")})
        if self.get("next"):
            self.set_state({"index" : self._current_index + 1})
        if self.get("randomize"):
            index = (self._current_index + random.randint(1, self._count - 1)) % self._count
            self.set_state({"index" : index})

        if self._current_index != -1:
            in_texture = self.get_input("in%d" % self._current_index)
            out_texture = self.get_output("out")
            in_texture.copy_to(out_texture)

    def get_state(self):
        return {"index" : self._current_index}

    def set_state(self, state):
        if "index" in state:
            # may be called before count is available, so just set next index
            if self._count is None:
                self._next_index = state["index"]
            else:
                self._set_next(state["index"])
                self.force_evaluate()

