#!/usr/bin/env python3

from glumpy import app, gl, glm, gloo, data, key
from glumpy.ext import glfw
from rendering import stage, transform, video, var, util
from rendering.generative import *

app.use("glfw")
window = app.Window()

keys = Keys(window)
key_space = keys[key.SPACE]
key_right = keys[key.RIGHT]

current_background = Iterated(key_right, shuffle=True, stages=[
    stage.TextureStage(util.load_texture(name)) for name in util.glob_textures("industrial/*")
])

#current_foreground = Iterated(key_right, shuffle=True, stages=[
#    stage.TextureStage(util.load_texture(name)) for name in util.glob_textures("industrial/*")
#])
current_foreground = current_background

current_mask = Iterated(key_space, shuffle=True, stages=[
    stage.TextureStage(util.load_texture(name), transform=[transform.scale(0.65)], force_size=(1920, 1080)) for name in util.glob_textures("mask/industrial/*")
])

mask = stage.Pipeline()
mask.add_stage(current_mask)

foreground = stage.Pipeline()
foreground.add_stage(current_foreground)
foreground.add_stage(stage.MaskStage(mask))
foreground.add_stage(stage.ShaderStage("common/passthrough.vert", "common/red.frag"))

background = stage.Pipeline()
background.add_stage(current_background)

pipeline = stage.Pipeline()
pipeline.add_stage(background)
pipeline.add_stage(foreground)

import visualapp
visualapp.run(window, pipeline)

