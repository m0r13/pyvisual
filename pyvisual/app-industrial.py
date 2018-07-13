#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import math
import logging
from glumpy import app, gl, glm, gloo, data, key
from glumpy.ext import glfw

from pyvisual.rendering import stage, transform, video, var, util
from pyvisual.rendering.generative import *
from pyvisual.event import *
from pyvisual.audio import analyzer
from pyvisual import visualapp

logging.basicConfig(level=logging.INFO)

app.use("glfw")
window = app.Window()

audio = analyzer.AudioAnalyzer()
beat_on = audio.beat_on
beat_status = audio.beat_status
vu = audio.vu

time = var.RelativeTime()
vu_norm = audio.vu_norm.as_var

keys = Keys(window)
key_space = keys[key.SPACE]
key_right = keys[key.RIGHT]

current_background = Iterated(key_right, shuffle=True, stages=[
    stage.TextureStage(util.load_texture(name)) for name in util.glob_textures("industrial/*")
])

current_foreground = Iterated(key_right, shuffle=True, stages=[
    stage.TextureStage(util.load_texture(name)) for name in util.glob_textures("industrial/*")
])
#current_foreground = current_background

scale = var.Time().apply(lambda x: math.sin(x)).map_range(-1, 1, 0.5, 0.9)
scale = vu_norm.map_range(0.0, 1.0, 0.5, 0.9)
#scale = var.Var.lerp(beat_status.as_var, 0.0, 1.0)
scale = 0.7
current_mask = Iterated(key_space, shuffle=True, stages=[
    stage.TextureStage(util.load_texture(name), transform=[transform.scale(scale)], force_size=(1920, 1080)) for name in util.glob_textures("mask/industrial/*")
])

def effect_mirror(*args):
    mirror_uniforms = {
        "uMode" : np.random.randint(low=0, high=4)
    }

    return stage.ShaderStage("common/passthrough.vert", "post/mirror.frag", mirror_uniforms)


mask = stage.Pipeline()
mask.add_stage(current_mask)
mask.add_stage(Selected(key_space, min_n=1, max_n=1, stages=[
    #stage.ShaderStage("common/passthrough.vert", "common/passthrough.frag", transform=[transform.zrotate(var.Time() * 10.0)]),
    stage.ShaderStage("common/passthrough.vert", "post/glitchbw.frag", {
        "time" : time,
        "amount" : var.Var.lerp(beat_status.as_var, 0.05 * 0.1, 0.05 * 3),
        "speed" : 0.1
    })
]))

foreground = stage.Pipeline()
foreground.add_stage(current_foreground)
foreground.add_stage(stage.MaskStage(mask))
foreground.add_stage(stage.ShaderStage("common/passthrough.vert", "common/red.frag"))

background = stage.Pipeline()
background.add_stage(current_background)
background.add_stage(Selected(key_space, min_n=1, max_n=1, stages=[
    effect_mirror
]))

pipeline = stage.Pipeline()
pipeline.add_stage(background)
pipeline.add_stage(foreground)
#pipeline.add_stage(mask)

visualapp.run(window, audio, pipeline)

