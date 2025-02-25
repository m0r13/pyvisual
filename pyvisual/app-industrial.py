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

change = EveryOnEvent(beat_on, every_n=8)
changes = MultiEvent(change, [
    "background",
    "foreground",
    "mask",

    "background_effect",
    "foreground_completely",
])

current_background = Iterated(key_right | changes["background"], shuffle=True, stages=[
    stage.TextureStage(util.load_texture(name)) for name in util.glob_textures("industrial/*")
])

current_foreground = Iterated(key_right | changes["foreground"] | changes["foreground_completely"], shuffle=True, stages=[
    stage.TextureStage(util.load_texture(name)) for name in util.glob_textures("industrial/*")
])
#current_foreground = current_background

scale = var.Time().apply(lambda x: math.sin(x)).map_range(-1, 1, 0.5, 0.9)
scale = vu_norm.map_range(0.0, 1.0, 0.5, 0.9)
current_mask = Iterated(key_space | changes["mask"] | changes["foreground_completely"], shuffle=True, stages=[
    stage.TextureStage(util.load_texture(name), transform=[transform.scale(scale)], force_size=(1920, 1080)) for name in util.glob_textures("mask/industrial/*")
])

def effect_mirror():
    def _effect(*args):
        mode = np.random.randint(low=0, high=4)
        effect = stage.Pipeline()
        if mode == 3:
            # horizontal and vertical mirrored
            angle = math.radians(np.random.randint(low=0, high=7) * 45.0)
            effect.add_stage(stage.ShaderStage("common/passthrough.vert", "post/move.frag", {"uDirection" : angle, "uDirectionOffset" : time * 25.0}))
        effect.add_stage(stage.ShaderStage("common/passthrough.vert", "post/mirror.frag", {"uMode" : mode}))
        return effect
    return _effect

def effect_slices():
    def _effect(*args):
        return stage.ShaderStage("common/passthrough.vert", "post/slices.frag", {
            "slices" : 3.0,
            "offset" : 0.03,
            "time" : time * 0.1,
            "speedV" : 0.3
        })
    return _effect

def effect_glitch(bw=False):
    def _effect(*args):
        fragment = "post/glitchbw.frag" if bw else "post/glitch.frag"
        return stage.ShaderStage("common/passthrough.vert", fragment, {
            "time" : time,
            "amount" : var.lerp(beat_status.as_var, 0.05 * 0.1, 0.05 * 3),
            "speed" : 0.1
        })
    return _effect

mask = stage.Pipeline()
mask.add_stage(current_mask)
mask.add_stage(Selected(keys[ord("M")], min_n=1, max_n=1, stages=[
    #stage.ShaderStage("common/passthrough.vert", "common/passthrough.frag", transform=[transform.zrotate(var.Time() * 10.0)]),
    effect_glitch(bw=True)
]))

foreground = stage.Pipeline()
foreground.add_stage(current_foreground)
foreground.add_stage(stage.MaskStage(mask))
foreground.add_stage(stage.ShaderStage("common/passthrough.vert", "common/red.frag"))

background = stage.Pipeline()
background.add_stage(current_background)
background.add_stage(Selected(keys[ord("B")] | changes["background_effect"], min_n=1, max_n=2, stages=[
    effect_mirror(),
    effect_slices()
]))

pipeline = stage.Pipeline()
pipeline.add_stage(background)
pipeline.add_stage(foreground)
#pipeline.add_stage(mask)

visualapp.run(window, audio, pipeline)

