import numpy as np
import time
from PIL import Image
from glumpy import app, gl, glm, gloo, data

class TextureQuad(gloo.Program):
    def __init__(self, vertex, fragment):
        if not "{" in vertex:
            vertex = open("data/shader/" + vertex, "r").read()
        if not "{" in fragment:
            fragment = open("data/shader/" + fragment, "r").read()

        super().__init__(vertex, fragment, count=4, version="130")
        self["iPosition"] = [(-1,-1), (-1,+1), (+1,-1), (+1,+1)]
        self["iTexCoord"] = [( 0, 1), ( 0, 0), ( 1, 1), ( 1, 0)]

    def render(self, texture, model_view_projection):
        self["uModelViewProjection"] = model_view_projection
        self["uInputTexture"] = texture
        self.draw(gl.GL_TRIANGLE_STRIP)

class Stage:
    def __init__(self, force_size=None, transform=lambda model: model):
        self._fbo = None
        self._force_size = force_size

        self._transform_model = transform
        self._transform_flipy = False

    def before_render(self, texture):
        pass
    def render(self, texture, target_size):
        pass
    def after_render(self):
        pass

    @property
    def preferred_size(self):
        return None

    def fbo(self, size):
        if self._fbo is not None:
            h, w, _ = self._fbo.color[0].shape
            if size == (w, h):
                return self._fbo
        w, h = size
        texture = np.zeros((h, w, 4), dtype=np.uint8).view(gloo.Texture2D)
        self._fbo = gloo.FrameBuffer(color=[texture])
        return self._fbo

    def _create_transformation(self, texture_size, target_size):
        texture_aspect = texture_size[0] / texture_size[1]
        target_aspect = target_size[0] / target_size[1]

        model = np.eye(4, dtype=np.float32)
        view = np.eye(4, dtype=np.float32)
        projection = glm.ortho(-1.0, 1.0, -1.0, 1.0, -1.0, 1.0)

        if texture_aspect < target_aspect:
            # border left/right
            height = target_size[1]
            width = int(texture_aspect * height)
            margin = (target_size[0] - width) // 2
            glm.scale(model, texture_aspect, 1.0, 1.0)
            glm.scale(projection, 1.0 / target_aspect, 1.0, 1.0)
        else:
            # border top/bottom
            width = target_size[0]
            height = int(width / texture_aspect)
            margin = (target_size[1] - height) // 2
            glm.scale(model, 1.0, 1.0 / texture_aspect, 1.0)
            glm.scale(projection, 1.0, target_aspect, 1.0)

        return model, view, projection

    def transform_input(self, texture_size, target_size):
        model, view, projection = self._create_transformation(texture_size, target_size)
        if self._transform_flipy:
            glm.scale(model, 1.0, -1.0, 1.0)
        return np.dot(model, np.dot(view, projection))

    def transform_destination(self, texture_size, target_size):
        model, view, projection = self._create_transformation(texture_size, target_size)
        model = self._transform_model(model)
        if self._transform_flipy:
            glm.scale(model, 1.0, -1.0, 1.0)
        return np.dot(model, np.dot(view, projection))

    def render_texture(self, texture):
        self.before_render(texture)

        #print("Rendering %s to texture" % repr(self))
        fbo_size = None
        if self._force_size is not None:
            fbo_size = self._force_size
        elif texture is not None:
            h, w, _ = texture.shape
            fbo_size = w, h
        elif self.preferred_size is not None:
            fbo_size = self.preferred_size
        else:
            assert False, "A preferred size must be set if there is no input texture / no size forced"

        fbo = self.fbo(fbo_size)
        fbo.activate()

        gl.glViewport(0, 0, fbo_size[0], fbo_size[1])
        gl.glClearColor(0.0, 0.0, 0.0, 0.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        self._transform_flipy = True
        self.render(texture, fbo_size)
        fbo.deactivate()
        self.after_render()

        return fbo.color[0]

    def render_screen(self, texture, screen_size):
        self.before_render(texture)
 
        #print("Rendering %s to screen" % repr(self))
        gl.glViewport(0, 0, screen_size[0], screen_size[1])

        self._transform_flipy = False
        self.render(texture, screen_size)
        self.after_render()

class ShaderStage(Stage):
    def __init__(self, vertex, fragment, configure_program=lambda quad: None, **kwargs):
        super().__init__(**kwargs)

        self._configure_program = configure_program
        self._quad = TextureQuad(vertex, fragment)

    def before_render(self, texture):
        self._configure_program(self._quad)

    def render(self, texture, target_size):
        h, w, _ = texture.shape
        mvp = self.transform_destination((w, h), target_size)
        self._quad.render(texture, mvp)

    @property
    def preferred_size(self):
        return None

class TextureStage(Stage):
    def __init__(self, texture=np.zeros((1, 1, 4), dtype=np.uint8), **kwargs):
        super().__init__(**kwargs)

        self._texture = texture.view(gloo.Texture2D)
        self._quad = TextureQuad("common/passthrough.vert", "common/passthrough.frag")

    @property
    def texture(self):
        return self._texture
    @texture.setter
    def texture(self, texture):
        self._texture = texture

    def render(self, texture, target_size):
        if texture is not None:
            h, w, _ = texture.shape
            mvp = self.transform_input((w, h), target_size)
            self._quad.render(texture, mvp)

        mvp = self.transform_destination(self.preferred_size, target_size)
        self._quad.render(self._texture, mvp)

    @property
    def preferred_size(self):
        h, w, _ = self._texture.shape
        return w, h

class VideoStage(TextureStage):
    def __init__(self, video, **kwargs):
        self._video = video
        self._texture = self._video.current_frame
        # we're calling this later because TextureStage constructor wants a texture
        super().__init__(self._texture, **kwargs)

    def render(self, texture, target_size):
        self._texture[:, :, :] = self._video.current_frame
        super().render(texture, target_size)

class MaskStage(ShaderStage):
    def __init__(self, mask, **kwargs):
        super().__init__("common/passthrough.vert", "common/mask.frag", **kwargs)

        self._mask_pipeline = None
        self._mask = None

        if isinstance(mask, Pipeline):
            self._mask_pipeline = mask
        else:
            self._mask = mask.view(gloo.Texture2D)

    def before_render(self, texture):
        if self._mask_pipeline:
            self._mask = self._mask_pipeline.render_texture(None)
        self._quad["uMaskTexture"] = self._mask

class Pipeline(Stage):
    def __init__(self, stages=[]):
        self._stages = stages
        self._fbos = None
        self._fbo_size = None

    def add_stage(self, stage):
        if isinstance(stage, Pipeline):
            stage = SubPipeline(stage)
        self._stages.append(stage)

    def add_shader(self, vertex, fragment, configure_program=lambda quad: None):
        self.add_stage(ShaderStage(vertex, fragment, configure_program))

    def clear_stages(self):
        self._stages = []

    def _pre_render(self, texture):
        for i, stage in enumerate(self._stages[:-1]):
            texture = stage.render_texture(texture)
        return self._stages[-1], texture

    def render_texture(self, texture):
        last_stage, texture = self._pre_render(texture)
        return last_stage.render_texture(texture)

    def render_screen(self, texture, screen_size):
        last_stage, texture = self._pre_render(texture)
        return last_stage.render_screen(texture, screen_size)

class SubPipeline(Pipeline):
    def __init__(self, pipeline):
        self._pipeline = pipeline
        self._compositor = TextureStage()

    def _render_pipeline(self):
        return self._pipeline.render_texture(None)

    def render_texture(self, texture):
        self._compositor.texture = self._render_pipeline()
        return self._compositor.render_texture(texture)

    def render_screen(self, texture, screen_size):
        self._compositor.texture = self._render_pipeline()
        return self._compositor.render_screen(texture, screen_size)

