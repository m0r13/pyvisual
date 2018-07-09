#!/usr/bin/env python3

import numpy as np
import time
import random
from PIL import Image
from glumpy import app, gl, glm, gloo, data, key
from glumpy.ext import glfw
from rendering import stage, transform, video, var, util
from rendering.generative import *

app.use("glfw")
window = app.Window()

keys = Keys()
timer = TimerEvent(1.0)

test = EveryOnEvent(timer, 2)
test = test | keys[(glfw.GLFW_KEY_A, 0)]
test = MultiEvent(test, ["a", "b"])

@window.event
def on_draw(dt):
    app.clock.tick()
    window.clear()

    w, h = window.get_size()
    pipeline.render_screen(None, (w, h))

    Event.reset_instances()
    GenerativeStage.reset_instances()

@window.event
def on_key_press(symbol, modifiers):
    # q
    if symbol == 81:
        window.close()

@window.event
def on_resize(width, height):
    pass

@window.event
def on_init():
    app.clock.set_fps_limit(30)

    keys.attach(window)

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
app.run()
