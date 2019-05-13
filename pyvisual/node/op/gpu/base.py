import math
import numpy as np
import traceback
import random
import imgui
import os
import json
from pyvisual.node.base import Node
from pyvisual.node import dtype
from pyvisual.node.op.gpu import custom_meta
from pyvisual.editor import widget
from pyvisual import assets
from glumpy import gloo, gl, glm
from PIL import Image

class RenderNode(Node):
    class Meta:
        options = {
            "virtual" : True
        }

    USES_OPENGL = True

    def __init__(self):
        super().__init__()

        self._fbo = None

    def get_fbo(self, size):
        if self._fbo is not None:
            h, w, _ = self._fbo.color[0].shape
            if size == (w, h):
                return self._fbo
        w, h = size
        texture = np.zeros((h, w, 4), dtype=np.uint8).view(gloo.Texture2D)
        self._fbo = gloo.FrameBuffer(color=[texture])
        return self._fbo

    def create_transform(self, m, texture_size, target_size):
        texture_aspect = texture_size[0] / texture_size[1]
        target_aspect = target_size[0] / target_size[1]

        model = np.eye(4, dtype=np.float32)
        view = np.eye(4, dtype=np.float32)
        projection = glm.ortho(-1.0, 1.0, -1.0, 1.0, -1.0, 1.0)
        texture = np.eye(4, dtype=np.float32)

        if abs(texture_aspect - target_aspect) < 0.1:
            pass
        elif texture_aspect < target_aspect:
            # border left/right
            glm.scale(model, texture_aspect, 1.0, 1.0)
            #glm.scale(projection, 1.0 / target_aspect, 1.0, 1.0)
            glm.scale(texture, target_aspect, 1.0, 1.0)
        else:
            # border top/bottom
            glm.scale(model, 1.0, 1.0 / texture_aspect, 1.0)
            #glm.scale(projection, 1.0, target_aspect, 1.0)
            glm.scale(texture, 1.0, 1.0 / target_aspect, 1.0)

        model = np.dot(model, m)

        glm.scale(model, 1.0, -1.0, 1.0)

        return model, view, projection, texture

    def render(self, size, render_func):
        fbo = self.get_fbo(size)
        fbo.activate()

        gl.glViewport(0, 0, size[0], size[1])
        gl.glClearColor(0.0, 0.0, 0.0, 0.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        render_func()

        fbo.deactivate()
        return fbo.color[0]

# TODO
dummy = np.zeros((1, 1, 4), dtype=np.uint8).view(gloo.Texture2D)

WRAPPING_MODES = ["repeat", "mirrored repeat", "clamp to edge", "clamp to border"]
WRAPPING_MODES_GL = [gl.GL_REPEAT, gl.GL_MIRRORED_REPEAT, gl.GL_CLAMP_TO_EDGE, gl.GL_CLAMP_TO_BORDER]
INTERPOLATION_MODES = ["nearest", "linear"]
INTERPOLATION_MODES_GL = [gl.GL_NEAREST, gl.GL_LINEAR]

# mapping of glsl data types to dtype's
GL_TO_DTYPE = {
    "bool" : dtype.bool,
    "int" : dtype.int,
    "float" : dtype.float,
    "vec2" : dtype.vec2,
    "vec4" : dtype.color,
    "mat4" : dtype.mat4,
    "sampler2D" : dtype.tex2d,
}

# mapping of dtype's to functions converting values for preprocessor value generation
PREPROCESSOR_DTYPES = {
    dtype.bool : lambda v: str(int(v)),
    dtype.int : lambda v: str(int(v)),
    dtype.float : str,
}

# it's called BaseShader to keep compatibility with some nodes
# might be changeable soon
class BaseShader(RenderNode):
    class Meta:
        inputs = [
            {"name" : "enabled", "dtype" : dtype.bool, "dtype_args" : {"default" : 1.0}},
            {"name" : "transformUV", "dtype" : dtype.mat4},
            {"name" : "sizeref", "dtype" : dtype.tex2d},
            {"name" : "input", "dtype" : dtype.tex2d},
            {"name" : "wrapping", "dtype" : dtype.int, "dtype_args" : {"default" : 1, "choices" : WRAPPING_MODES}, "group" : "additional"},
            {"name" : "interpolation", "dtype" : dtype.int, "dtype_args" : {"default" : 1, "choices" : INTERPOLATION_MODES}, "group" : "additional"},
        ]
        outputs = [
            {"name" : "enabled", "dtype" : dtype.bool, "dtype_args" : {"default" : 1.0}},
            {"name" : "output", "dtype" : dtype.tex2d}
        ]
        options = {
            "virtual" : True
        }

    def __init__(self, vertex_source, fragment_source, handle_uniforms=False):
        super().__init__()

        self.quad = None
        self.shader_error = None

        # mapping of inputs to program preprocessor values
        self._input_preprocessor_mapping = []
        # list of preprocessor input values. used as faster access when checking if shader needs to be rebuilt
        self._preprocessor_values = []

        # mapping of inputs to program uniforms (if uniforms should be handled)
        # returned by _parse_uniform_inputs, set when building program
        self._input_uniform_mapping = []

        self.vertex_source = vertex_source
        self.fragment_source = fragment_source
        # whenever to parse shader sources, generate node inputs and
        # set uniforms during evaluation
        self.handle_uniforms = handle_uniforms
        # don't initialize program here, but at first evaluation
        # because saved input values are not available yet here
        # or maybe there is a better way?
        #self.update_program()

        self.input_texture = None

    @property
    def wrapping(self):
        mode = int(self.get("wrapping"))
        mode = max(0, min(len(WRAPPING_MODES), mode))
        return WRAPPING_MODES_GL[mode]

    @property
    def interpolation(self):
        mode = int(self.get("interpolation"))
        mode = max(0, min(len(INTERPOLATION_MODES), mode))
        return INTERPOLATION_MODES_GL[mode]

    def _parse_preprocessor_inputs(self, fragment_source):
        # returns these two lists:
        # list of tuples (input value name, preprocessor value name, default value, value transform function)
        input_preprocessor_mapping = []
        # list of port specs representing preprocessor inputs
        preprocessor_ports = []

        inputs = assets.parse_shader_preprocessor_inputs(fragment_source)
        for gltype, name, kwargs in inputs:
            if not gltype in GL_TO_DTYPE:
                raise RuntimeError("Unsupported glsl data type '%s' as node port input" % gltype)

            if kwargs.get("skip", False):
                continue

            preprocessor_name = name
            input_name = kwargs.get("alias", name)
            port_spec = {"name" : input_name, "dtype" : GL_TO_DTYPE[gltype]}
            if not port_spec["dtype"] in PREPROCESSOR_DTYPES:
                raise ValueError("Unsupported data type '%s' as shader preprocessor input" % gltype)

            default = port_spec["dtype"].default
            if "default" in kwargs:
                default = port_spec["dtype"].base_type.unserialize(kwargs["default"])

            dtype_args = {"default" : default}
            if port_spec["dtype"] == dtype.int and "choices" in kwargs:
                dtype_args["choices"] = kwargs["choices"]
            if "range" in kwargs:
                dtype_args["range"] = kwargs["range"]
            if "unit" in kwargs:
                dtype_args["unit"] = kwargs["unit"]
            if "group" in kwargs:
                port_spec["group"] = kwargs["group"]
            port_spec["dtype_args"] = dtype_args

            value_transform = PREPROCESSOR_DTYPES[port_spec["dtype"]]
            input_preprocessor_mapping.append((input_name, preprocessor_name, default, value_transform))
            preprocessor_ports.append(port_spec)
        return input_preprocessor_mapping, preprocessor_ports

    def _generate_preprocessor_input_defines(self, input_preprocessor_mapping):
        defines = ""
        for input_name, preprocessor_name, default, value_transform in input_preprocessor_mapping:
            # a preprocessor input might be new in a shader => no input port / value yet
            # use the default value unless there is an input value
            value = default
            if "i_" + input_name in self.values:
                value = self.get(input_name)
            defines += "#define %s %s\n" % (preprocessor_name, value_transform(value))
        return defines

    def _parse_uniform_inputs(self, vertex_source, fragment_source):
        # returns these two lists
        # list of tuples (input port name, uniform name, dtype)
        input_uniform_mapping = []
        # port_specs suitable to set as custom input ports
        input_ports = []

        uniforms = assets.parse_shader_uniform_inputs(vertex_source, fragment_source)
        for gltype, name, kwargs in uniforms:
            if not gltype in GL_TO_DTYPE:
                raise RuntimeError("Unsupported glsl data type '%s' as node port input" % gltype)

            if kwargs.get("skip", False):
                continue

            uniform_name = name
            input_name = kwargs.get("alias", name)
            port_spec = {"name" : input_name, "dtype" : GL_TO_DTYPE[gltype]}

            dtype_args = {}
            if port_spec["dtype"] == dtype.int and "choices" in kwargs:
                dtype_args["choices"] = kwargs["choices"]
            if "default" in kwargs:
                dtype_args["default"] = port_spec["dtype"].base_type.unserialize(kwargs["default"])
            if "range" in kwargs:
                dtype_args["range"] = kwargs["range"]
            if "unit" in kwargs:
                dtype_args["unit"] = kwargs["unit"]
            if "group" in kwargs:
                port_spec["group"] = kwargs["group"]
            port_spec["dtype_args"] = dtype_args

            input_uniform_mapping.append((input_name, uniform_name, port_spec["dtype"]))
            input_ports.append(port_spec)

        return input_uniform_mapping, input_ports

    def _process_uniform_inputs(self, port_specs):
        # called when uniforms of shader are parsed
        # and node inputs are generated from these
        # you can override this method in a subclass (for example Filter)
        pass

    def update_program(self):
        vertex = self.vertex_source.data
        fragment = self.fragment_source.data

        # TODO this check if shaders are not empty is very rudimentary!
        if not vertex or not fragment or not "void main" in fragment:
            print("### Warning: Empty vertex/fragment shader of node %s #%d" % (self, self.id))
            self.quad = None
            self.shader_error = "Empty vertex/fragment shader"
            return

        # gather preprocessor/uniform inputs from shader sources
        input_preprocessor_mapping, preprocessor_ports = self._parse_preprocessor_inputs(fragment)
        input_uniform_mapping, uniform_ports = self._parse_uniform_inputs(vertex, fragment)

        # add preprocessor inputs to fragment shader source
        fragment = self._generate_preprocessor_input_defines(input_preprocessor_mapping) + fragment

        try:
            if self.quad:
                self.quad.delete()
            self.quad = gloo.Program(vertex, fragment, version="430", count=4)
            self.quad["iPosition"] = [(-1,-1), (-1,+1), (+1,-1), (+1,+1)]
            self.quad["iTexCoord"] = [( 0, 1), ( 0, 0), ( 1, 1), ( 1, 0)]

            # HACKY
            # we want to check if the built shader program compiles
            # need to run it once
            # but also set all uniform textures to dummy textures, otherwise it doesn't work
            # (that's how it's possible with glumpy at the moment)
            for uniform, gtype in self.quad.all_uniforms:
                if gtype == gl.GL_SAMPLER_2D:
                    self.quad[uniform] = dummy
            self.quad.draw(gl.GL_TRIANGLE_STRIP)
            self.shader_error = None

            # create custom input ports from preprocessor/uniform inputs
            if self.handle_uniforms:
                self._input_preprocessor_mapping = input_preprocessor_mapping
                self._input_uniform_mapping = input_uniform_mapping
                # allow subclasses to modify uniform inputs, see _process_uniform_inputs
                self._process_uniform_inputs(uniform_ports)
                self.set_custom_inputs(preprocessor_ports + uniform_ports)
            else:
                self.set_custom_inputs(uniform_ports)

            # after custom ports have been generated:
            # put input values of preprocessor inputs in a list for faster checking if a shader program update is required
            # when one of these values has changed
            self._preprocessor_values = []
            for input_name, _, _, _ in input_preprocessor_mapping:
                self._preprocessor_values.append(self.get_input(input_name))

            # force a new evaluation after the shader program has been updated
            self.force_evaluate()
        except Exception as e:
            if self.quad:
                self.quad.delete()
            self.quad = None
            self.shader_error = traceback.format_exc()
            traceback.print_exc()
            print("Error happened in class %s, node %d" % (self, self.id))

    def set_uniforms(self, program):
        for input_name, uniform_name, dt in self._input_uniform_mapping:
            value = self.get(input_name)
            if dt == dtype.tex2d and value is None:
                value = dummy
            elif dt == dtype.bool:
                value = int(value)
            program[uniform_name] = value

    def evaluate(self):
        # update program if shader source has changed, on first evaluation, or if a preprocessor input value has changed
        if self.vertex_source.has_changed or self.fragment_source.has_changed or self._last_evaluated == 0.0:
            self.update_program()
        else:
            for value in self._preprocessor_values:
                if value.has_changed:
                    self.update_program()
                    break

        return super().evaluate()

    def _evaluate(self):
        enabled = self.get("enabled")
        self.set("enabled", enabled)
        if not enabled or self.quad is None:
            self.set("output", self.get("input"))
            return

        self.input_texture = self.get("input")
        sizeref = self.get("sizeref")
        # TODO what to do?!
        if self.input_texture is None:
            # if there is no input texture, there must be a sizeref texture at least
            # input texture is empty texture then
            # useful for shaders that generate some image data
            if sizeref is None:
                self.set("output", None)
                return
            self.input_texture = dummy

        if sizeref is None:
            sizeref = self.input_texture
        texture_size = self.input_texture.shape[:2][::-1]
        target_size = sizeref.shape[:2][::-1]
        def do_render():
            custom_model = np.eye(4, dtype=np.float32)
            model, view, projection, texture = self.create_transform(custom_model, texture_size, target_size)
            self.quad["uModelViewProjection"] = np.dot(model, np.dot(view, projection))
            self.quad["uTextureSize"] = texture_size
            self.quad["uTransformUV"] = np.dot(texture, self.get("transformUV"))
            self.input_texture.interpolation = self.interpolation
            self.input_texture.wrapping = self.wrapping
            self.quad["uInputTexture"] = self.input_texture
            self.set_uniforms(self.quad)
            self.quad.draw(gl.GL_TRIANGLE_STRIP)

        self.set("output", self.render(target_size, do_render))

    def _show_custom_ui(self):
        if self.shader_error is None:
            return

        imgui.dummy(1, 5)
        imgui.text_colored("Shader error. (?)", 1.0, 0.0, 0.0)
        if imgui.is_item_hovered():
            imgui.set_tooltip(self.shader_error)

    def _show_custom_context(self):
        if imgui.button("reload shaders"):
            self.update_program()

        super()._show_custom_context()

class Shader(BaseShader):
    class Meta:
        options = {
            "virtual" : True
        }

    def __init__(self, vertex, fragment, **kwargs):
        vertex_path = assets.get_shader_path(vertex)
        fragment_path = assets.get_shader_path(fragment)

        super().__init__(assets.FileShaderSource(vertex_path), assets.FileShaderSource(fragment_path), **kwargs)

class ShaderNodeLoader():

    instances = []

    def __init__(self, wildcard, baseclass, module, globals_):
        self._wildcard = wildcard
        self._baseclass = baseclass
        self._module = module
        self._globals = globals_

        self._classes = {}

        self.instances.append(self)

        self.reload()

    def reload(self):
        baseclass = self._baseclass
        module = self._module
        g = self._globals
        for path in assets.glob_paths(self._wildcard):
            name = os.path.basename(path).replace(".frag", "")
            if name == "base":
                continue
            if name in g:
                if not issubclass(g[name], self._baseclass):
                    print("### Warning: Seems that class name %s in module %s is already taken" % (name, module))
                else:
                    # filter class already exist, no need to recreate it for now
                    continue

            meta = None
            meta_name = "%sMeta" % name
            if meta_name in dir(custom_meta):
                meta = getattr(custom_meta, meta_name)
            else:
                meta = type("Meta", tuple(), {})

            fragment_path = path.replace("shader" + os.path.sep, "")
            attrs = {"FRAGMENT" : fragment_path, "Meta" : meta, "__module__" : module}
            filter_class = type(name, (baseclass,), attrs)
            g[name] = filter_class
            del filter_class

    @classmethod
    def reload_all(cls):
        for loader in cls.instances:
            loader.reload()

class Blend(RenderNode):
    class Meta:
        inputs = [
            {"name" : "input1", "dtype" : dtype.tex2d},
            {"name" : "input2", "dtype" : dtype.tex2d},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.tex2d}
        ]
        options = {
            "virtual" : False
        }

    def __init__(self):
        super().__init__()

        vertex_path = assets.get_shader_path("common/passthrough.vert")
        fragment_path = assets.get_shader_path("common/passthrough.frag")

        vertex = assets.load_shader(vertex_path)
        fragment = assets.load_shader(fragment_path)
        self.quad = gloo.Program(vertex, fragment, version="430", count=4)
        self.quad["iPosition"] = [(-1,-1), (-1,+1), (+1,-1), (+1,+1)]
        self.quad["iTexCoord"] = [( 0, 1), ( 0, 0), ( 1, 1), ( 1, 0)]

    def set_uniforms(self, program):
        pass

    def _evaluate(self):
        input1 = self.get("input1")
        input2 = self.get("input2")
        if input1 is None:
            self.set("output", None)
            return

        if input2 is None:
            self.set("output", input1)
            return

        target_size = input1.shape[:2][::-1]
        input1_size = input1.shape[:2][::-1]
        input2_size = input2.shape[:2][::-1]
        def do_render():
            eye = np.eye(4, dtype=np.float32)

            model, view, projection, transform_uv = self.create_transform(eye, input1_size, target_size)
            self.quad["uModelViewProjection"] = np.dot(model, np.dot(view, projection))
            self.quad["uTextureSize"] = input1_size
            self.quad["uTransformUV"] = transform_uv
            self.quad["uInputTexture"] = input1
            self.quad.draw(gl.GL_TRIANGLE_STRIP)

            model, view, projection, transform_uv = self.create_transform(eye, input2_size, target_size)
            self.quad["uModelViewProjection"] = np.dot(model, np.dot(view, projection))
            self.quad["uTextureSize"] = input2_size
            self.quad["uTransformUV"] = transform_uv
            self.quad["uInputTexture"] = input2
            self.quad.draw(gl.GL_TRIANGLE_STRIP)

        self.set("output", self.render(target_size, do_render))


