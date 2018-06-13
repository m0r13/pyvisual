#!/usr/bin/env python3

import numpy as np
import math
import cv2
import time
import threading
from glumpy import app, gl, glm, gloo, data
from pipeline import *
from video import *
import var

window = app.Window()

blah = data.get("lena.png").view(gloo.Texture2D)

@window.event
def on_draw(dt):
    app.clock.tick()
    window.clear()

    gl.glEnable(gl.GL_BLEND);
    gl.glBlendEquationSeparate(gl.GL_FUNC_ADD, gl.GL_FUNC_ADD);
    gl.glBlendFuncSeparate(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA, gl.GL_ONE, gl.GL_ONE_MINUS_SRC_ALPHA);

    w, h = window.get_size()
    #print("----------")
    pipeline.render_screen(None, (w, h))
    var.ReloadVar.reload_vars()

@window.event
def on_key_press(symbol, modifiers):
    # q
    if symbol == 81:
        window.close()
    if symbol == 32:
        video.paused = not video.paused

@window.event
def on_resize(width, height):
    pass

@window.event
def on_init():
    app.clock.set_fps_limit(30)

looper = ForwardBackward([2, 3], [1, 1], [1, 2], [1, 1])
video = VideoReader("/home/moritz/Videos/RickRoll.mp4", time_control=looper)
#video = VideoReader("/home/moritz/output.mp4", time_control=looper)
video.start()
video2 = VideoReader(0)
video2.start()

def flipy(model):
    #glm.scale(model, 1.0, -1.0, 1.0)
    return model

def video_transform(model):
    glm.zrotate(model, 15.0 * time.time())
    #glm.zrotate(model, 45)
    glm.scale(model, 0.5)
    return model
video_stage = VideoStage(video, transform=video_transform)
video2_stage = VideoStage(video2, transform=flipy)


triangle = np.array(Image.open("data/mask/triangle.png"))
def rotate_triangle(model):
    glm.zrotate(model, 15.0 * time.time())
    #glm.scale(model, float(size))
    return model

rombus = np.array(Image.open("data/mask/rect.png"))
def rotate_rombus(model):
    glm.zrotate(model, 15.0 * time.time())
    glm.scale(model, 0.5)
    return model

circle = np.array(Image.open("data/mask/circle.png"))
circle[:, :, 1] *= 0
circle[:, :, 2] *= 0
def transform_circle(model):
    glm.scale(model, 0.75)
    return model

speed = var.ReloadVar(2.0)
start = var.ReloadVar(0.2)
end = var.ReloadVar(1.0)
size = start + ((var.Time() * speed).apply(math.sin) + 1) * 0.5 * (end - start)
#mask = Pipeline([TextureStage(triangle, force_size=(320, 240))])
mask = Pipeline([TextureStage(triangle, transform=[rotate_triangle, transform.scale(size)], force_size=(320*3, 240*3))])
mask2 = Pipeline([TextureStage(circle, transform=[transform.scale(size)], force_size=(320*3, 240*3))])

pipeline = Pipeline()
#pipeline.add_stage(TextureStage(data.get("lena.png"), transform=flipy))
#pipeline.add_stage(Pipeline(stages=[video2_stage, ShaderStage(vertex, fragment)]))
#pipeline.add_stage(Pipeline(stages=[video_stage, ShaderStage("common/passthrough.vert", "common/passthrough.frag")]))
pipeline.add_stage(VideoStage(video, transform=flipy))
#pipeline.add_stage(ShaderStage("common/passthrough.vert", "common/passthrough.frag"))
pipeline.add_stage(Pipeline([VideoStage(video2, transform=flipy), MaskStage(mask2)]))
pipeline.add_stage(Pipeline([VideoStage(video2, transform=flipy), ShaderStage("common/passthrough.vert", "common/inv.frag"), MaskStage(mask)]))

#pipeline.add_stage(TextureStage(triangle, transform=rotate_triangle))
#pipeline.add_stage(TextureStage(rombus, transform=rotate_rombus))

#pipeline.add_stage(video_stage)
#pipeline.add_stage(ShaderStage(vertex, fragment_inv))
#pipeline.add_stage(ShaderStage(vertex, fragment))

#pipeline = TextureStage(data.get("lena.png"))
#pipeline = ShaderStage(vertex, fragment_inv)

app.run()
