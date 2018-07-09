#!/usr/bin/env python3

from glumpy import app, gl, glm, gloo, data, key
from glumpy.ext import glfw
from rendering import stage, transform, video, var, util
from rendering.generative import *

app.use("glfw")
window = app.Window()

keys = Keys(window)

none = ExprEvent(lambda: False)
key_space = keys[key.SPACE]
key_right = keys[key.RIGHT]
key_up = keys[key.UP]

def transition(*args):
    vertex = "common/passthrough.vert"
    fragment = None
    if key_right.value:
        fragment = "transition/move.frag"
        uniforms = {}
    if key_space.value:
        fragment = "transition/test.frag"
        uniforms = {"strength" : 0.2}
    return vertex, fragment, uniforms

pipeline = stage.Pipeline()
pipeline.add_stage(Transitioned(Iterated(key_right | key_space, shuffle=True, stages=[
    stage.TextureStage(util.load_texture(name)) for name in util.glob_textures("vapor/*")

]), transition))
pipeline.add_stage(Iterated(key_up, shuffle=True, stages=[
    stage.ShaderStage("common/passthrough.vert", "common/passthrough.frag"),
    stage.ShaderStage("common/passthrough.vert", "common/inv.frag"),
    stage.ShaderStage("common/passthrough.vert", "common/red.frag"),
]))

import visualapp
visualapp.run(window, pipeline)

