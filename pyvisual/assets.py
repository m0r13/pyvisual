
import os
import glob

ASSET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
SAVE_PATH = os.path.join(ASSET_PATH, "saves")

os.makedirs(SAVE_PATH, exist_ok=True)

def load_shader(name):
    path = os.path.join(ASSET_PATH, "shader", name)
    source = open(path, "r").read()
    return source

def glob_paths(wildcard):
    paths = []
    for path in glob.glob(os.path.join(ASSET_PATH, wildcard)):
        paths.append(os.path.relpath(path, ASSET_PATH))
    return paths

