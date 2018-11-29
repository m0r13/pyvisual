
import os
import glob
import time

ASSET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
SHADER_PATH = os.path.join(ASSET_PATH, "shader")
SAVE_PATH = os.path.join(ASSET_PATH, "saves")
SCREENSHOT_PATH = os.path.join(ASSET_PATH, "screenshots")

os.makedirs(SAVE_PATH, exist_ok=True)
os.makedirs(SCREENSHOT_PATH, exist_ok=True)

def get_shader_path(name):
    path = os.path.join(SHADER_PATH, name)
    if not path.startswith(os.path.abspath(SHADER_PATH) + os.sep):
        raise ValueError("Illegal shader path '%s', may not be outside of SHADER_PATH." % path)
    return path

class ShaderError(ValueError):
    pass

def read_shader(path):
    return open(get_shader_path(path), "r").read()

def preprocess_shader(source):
    # we could use a path as context here,
    # but let's just work with global paths everywhere for now

    # handle #include's
    lines = []
    for line in source.split("\n"):
        line = line.strip()
        if not "#include" in line:
            lines.append(line)
            continue

        prefix = "#include <"
        suffix = ">"
        if not line.startswith(prefix) or not line.endswith(suffix):
            raise ShaderError("Invalid #include line " + line)
        path = line[len(prefix):-len(suffix)]
        shader = preprocess_shader(read_shader(path))
        lines.extend(shader.split("\n"))

    return "\n".join(lines)

def load_shader(path=None, source=None):
    if path is None and source is None:
        raise ValueError("A path xor source must be provided.")
    if path is not None and source is not None:
        raise ValueError("A path xor source must be provided.")

    if path is not None:
        source = read_shader(path)
    source = preprocess_shader(source)

    return source

def parse_shader_uniforms(vertex_source, fragment_source):
    def parse_uniforms(source):
        uniforms = []
        for line in source.split("\n"):
            line = line.strip()
            if not line.startswith("uniform"):
                continue
            if "//" in line:
                line = line[:line.find("//")]
            parts = line.split(" ")
            if len(parts) < 3:
                continue
            gltype = parts[1]
            # remove trailing ";"
            name = parts[2][:-1]
            uniforms.append((gltype, name))
        return uniforms

    # TODO, should be okay for now
    # just take uniforms from fragment source
    # if there are more in vertex source, add them to the end
    uniforms = parse_uniforms(fragment_source)
    for uniform in parse_uniforms(vertex_source):
        if uniform not in uniforms:
            uniforms.append(uniform)

    return uniforms

def glob_paths(wildcard):
    paths = []
    for path in glob.glob(os.path.join(ASSET_PATH, wildcard)):
        paths.append(os.path.relpath(path, ASSET_PATH))
    return paths

class FileWatcher:
    CHECK_INTERVAL = 1.0

    def __init__(self, path):
        self.path = path
        self.last_check = 0

    def has_changed(self):
        t = time.time()
        if t - self.CHECK_INTERVAL > self.last_check:
            last_change = os.path.getmtime(self.path)
            changed = last_change > self.last_check
            self.last_check = t
            if changed:
                return True
        return False

