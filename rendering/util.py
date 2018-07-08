import os
import glob
import numpy as np
from PIL import Image
from glumpy import gloo

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")

cached_shaders = {}
def load_shader(name):
    global cached_shaders

    if name not in cached_shaders:
        path = os.path.join(DATA_PATH, "shader", name)
        source = open(path, "r").read()
        # hmmm seems that re-using shader objects is problematic
        return source

        extension = path.split(".")[-1]
        shader_type = {
            "vert" : gloo.VertexShader,
            "frag" : gloo.FragmentShader
        }[extension]
        shader = shader_type(source)
        cached_shaders[name] = shader_type(source)
        return shader
    return cached_shaders[name]

def load_texture(name):
    path = os.path.join(DATA_PATH, "image", name)
    return np.array(Image.open(path)).view(gloo.Texture2D)

def glob_textures(name):
    wildcard = os.path.join(DATA_PATH, "image", name)
    for path in glob.glob(wildcard):
        path = os.path.relpath(path, os.path.join(DATA_PATH, "image"))
        yield path
