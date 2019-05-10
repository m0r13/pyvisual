
import os
import glob
import time
import json

ASSET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
SHADER_PATH = os.path.join(ASSET_PATH, "shader")
SAVE_PATH = os.path.join(ASSET_PATH, "saves")
SCREENSHOT_PATH = os.path.join(ASSET_PATH, "screenshots")

os.makedirs(SAVE_PATH, exist_ok=True)
os.makedirs(SCREENSHOT_PATH, exist_ok=True)

def glob_paths(wildcard):
    paths = []
    for path in glob.glob(os.path.join(ASSET_PATH, wildcard)):
        paths.append(os.path.relpath(path, ASSET_PATH))
    return paths

def get_shader_path(name):
    assert name, "Shader path must not be empty"
    path = os.path.join(SHADER_PATH, name)
    if not path.startswith(os.path.abspath(SHADER_PATH) + os.sep):
        raise ValueError("Illegal shader path '%s', may not be outside of SHADER_PATH." % path)
    return path

class ShaderError(ValueError):
    pass

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
        shader = preprocess_shader(load_shader(path=path))
        lines.extend(shader.split("\n"))

    return "\n".join(lines)

def load_shader(path=None, source=None):
    if path is None and source is None:
        raise ValueError("A path xor source must be provided.")
    if path is not None and source is not None:
        raise ValueError("A path xor source must be provided.")

    if path is not None:
        source = open(get_shader_path(path), "r").read()
    source = preprocess_shader(source)

    return source

def parse_shader_preprocessor_inputs(shader_source):
    inputs = []
    for line in shader_source.split("\n"):
        line = line.strip()
        if not line.startswith("// preprocessor "):
            continue

        line = line[len("// "):]

        comment = None
        if ";" in line:
            comment_index = line.find(";")
            comment = line[comment_index+2:].strip()
            line = line[:comment_index]

        parts = line.split(" ")
        if len(parts) < 3:
            continue
        # extract opengl uniform type and uniform name
        gltype = parts[1]
        # remove trailing ";"
        name = parts[2]

        # in case there is a // comment after the uniform definition
        # attempt to parse json object after this
        kwargs = {}
        if comment and comment.startswith("{") and comment.endswith("}"):
            kwargs = json.loads(comment)

        # uniform is then opengl type, name, and other kw arguments
        inputs.append((gltype, name, kwargs))
    return inputs

def parse_shader_uniform_inputs(vertex_source, fragment_source):
    def parse_uniforms(source):
        inputs = []
        for line in source.split("\n"):
            line = line.strip()
            if not line.startswith("uniform"):
                continue

            comment = None
            if "//" in line:
                comment_index = line.find("//")
                comment = line[comment_index+2:].strip()
                line = line[:comment_index]

            parts = line.split(" ")
            if len(parts) < 3:
                continue
            # extract opengl uniform type and uniform name
            gltype = parts[1]
            # remove trailing ";"
            name = parts[2][:-1]

            # in case there is a // comment after the uniform definition
            # attempt to parse json object after this
            kwargs = {}
            if comment and comment.startswith("{") and comment.endswith("}"):
                kwargs = json.loads(comment)

            # uniform is then opengl type, name, and other kw arguments
            inputs.append((gltype, name, kwargs))
        return inputs

    # we assume that vertex/fragment shader don't share any uniforms
    inputs = parse_uniforms(vertex_source) + parse_uniforms(fragment_source)
    return inputs

class ShaderSource:
    @property
    def data(self):
        raise NotImplementedError()
    @property
    def has_changed(self):
        raise NotImplementedError()

class FileShaderSource(ShaderSource):
    def __init__(self, path):
        self._path = path
        self._watcher = FileWatcher(path)

    @property
    def data(self):
        return load_shader(path=self._path)

    @property
    def has_changed(self):
        return self._watcher.has_changed()

class StaticShaderSource(ShaderSource):
    def __init__(self):
        self._data = ""
        self._changed = False
    
    @property
    def data(self):
        return self._data
    @data.setter
    def data(self, data):
        self._data = data
        self._changed = True

    @property
    def has_changed(self):
        changed = self._changed
        self._changed = False
        return changed

class CustomDefineShaderSource(ShaderSource):
    def __init__(self, source, defines=set()):
        self._source = source
        self._defines = set(defines)
        self._has_changed = False

    def set(self, define, enabled):
        if not enabled:
            self._defines.discard(define)
        else:
            self._defines.add(define)
        self._has_changed = True

    @property
    def data(self):
        defines = "\n".join([ "#define %s" % define for define in self._defines ])
        data = defines + "\n" + self._source.data
        return data

    @property
    def has_changed(self):
        changed = self._source.has_changed or self._has_changed
        self._has_changed = False
        return changed

class FileWatcher:
    CHECK_INTERVAL = 1.0

    def __init__(self, path):
        self.path = path
        self.last_check = 0

    def has_changed(self):
        t = time.time()
        if t - self.CHECK_INTERVAL > self.last_check:
            last_check = self.last_check
            self.last_check = t
            try:
                last_change = os.path.getmtime(self.path)
                return last_change > last_check
            except FileNotFoundError:
                # might happen sometimes that a file doesn't exist anymore for a moment
                # when it is saved. dunno why
                return False
        return False

    def read(self):
        f = open(self.path)
        data = f.read()
        f.close()
        return data

