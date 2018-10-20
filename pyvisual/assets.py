
import os

ASSET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
SAVE_PATH = os.path.join(ASSET_PATH, "saves")

os.makedirs(SAVE_PATH, exist_ok=True)

def load_shader(name):
    path = os.path.join(ASSET_PATH, "shader", name)
    source = open(path, "r").read()
    return source
