#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import math
import logging
from glumpy import app, gl, glm, gloo, data, key
from glumpy.ext import glfw

from pyvisual.rendering import generative, stage, transform, video, var, util
from pyvisual.rendering.var import _V
from pyvisual.audio import analyzer
from pyvisual import visualapp, event

logging.basicConfig(level=logging.DEBUG)

app.use("glfw")
window = app.Window()

audio = analyzer.AudioAnalyzer()
beat_on = audio.beat_on
beat_status = audio.beat_status
vu = audio.vu

time = var.RelativeTime()
vu_norm = audio.vu_norm

keys = event.Keys(window)
key_space = keys[key.SPACE]
key_right = keys[key.RIGHT]

change = event.EveryOnEvent(beat_on, every_n=16)
changes = event.MultiEvent(change, {
    "background" : 1.0,
    "foreground" : 1.0,
    "mask" : 1.0,

    "background_effect" : 1.0,
    "foreground_completely" : 1.0
})

current_background = generative.Iterated(keys[key.LEFT] | changes["background"], shuffle=True, stages=
    generative.load_resources("vapor/color scheme 1/*.jpg")
)

current_foreground = generative.Iterated(key_right | changes["foreground"] | changes["foreground_completely"], shuffle=True, stages=
    generative.load_resources("vapor/color scheme 1/*.jpg")
)
#current_foreground = current_background

scale = var.Time().apply(lambda x: math.sin(x)).map_range(-1, 1, 0.5, 0.9)
scale = vu_norm.map_range(0.0, 1.0, 0.5, 0.9)

def mask_transition(*args):
    vertex = "common/passthrough.vert"
    fragment = "transition/lerp.frag"
    uniforms = {}
    duration = 0.5

    return vertex, fragment, uniforms, duration

current_mask = generative.Transitioned(generative.Iterated(key_space | changes["mask"] | changes["foreground_completely"], shuffle=True, stages=
    #generative.load_resources("mask/common/*.png", transform=[transform.scale(scale)], force_size=(1920, 1080))
    generative.load_resources("mask/test/*.png", transform=[transform.scale(scale)], force_size=(1920, 1080))

), transition_config=mask_transition)

def effect_mirror(mode=None):
    move = stage.ShaderStage("common/passthrough.vert", "post/move.frag")
    mirror = stage.ShaderStage("common/passthrough.vert", "post/mirror.frag")
    effect = stage.Pipeline([move, mirror])
    def _effect(*args):
        m = mode
        if m is None:
            m = np.random.randint(low=0, high=4)
        if m == 3:
            # horizontal and vertical mirrored
            angle = math.radians(np.random.randint(low=0, high=7) * 45.0)
            move.set_uniforms({"uDirection" : angle, "uDirectionOffset" : time * 25.0})
        mirror.set_uniforms({"uMode" : m})
        return effect
    return _effect

def effect_chromatic_aberration():
    effect = stage.ShaderStage("common/passthrough.vert", "post/chromaticaberration.frag")
    def _effect(*args):
        angle = np.random.uniform(math.radians(0.0), np.radians(360.0), size=(4,))
        rotation = np.random.uniform(low=-0.5, high=0.5, size=(4,))
        offset = np.random.uniform(low=0.0, high=25.0, size=(4,))
        def uniforms(program):
            t = float(time)
            stage.apply_uniforms(program, {
                "uDirections" : angle + t * rotation,
                "uDirectionsOffset" : offset
            })
        effect.set_uniforms(uniforms)
        return effect
    return _effect

def effect_slices():
    effect = stage.ShaderStage("common/passthrough.vert", "post/slices.frag")
    def _effect(*args):
        effect.set_uniforms({
            "slices" : 3.0,
            "offset" : 0.03,
            "time" : time * 0.1,
            "speedV" : 0.3
        })
        return effect
    return _effect

def effect_scanlines_fine():
    effect = stage.ShaderStage("common/passthrough.vert", "post/scanline.frag")
    def _effect(*args):
        effect.set_uniforms({
            "time" : time,
            "count" : 400.0,
            "noiseAmount" : 0.25,
            "linesAmount" : 0.25
        })
        return effect
    return _effect

def effect_scanlines_coarse():
    effect = stage.ShaderStage("common/passthrough.vert", "post/scanlinescoarse.frag")
    seed = np.random.uniform(low=0.0, high=10.0)
    def _effect(*args):
        effect.set_uniforms({
            "uNoiseTexture" : util.load_texture("noise3.png"),
            "time" : time + seed
        })
        return effect
    return _effect

def effect_glitch(bw=False):
    def _effect(*args):
        fragment = "post/glitchbw.frag" if bw else "post/glitch.frag"
        return stage.ShaderStage("common/passthrough.vert", fragment, {
            "time" : time,
            "amount" : var.lerp(beat_status, 0.05 * 0.1, 0.05 * 3),
            "speed" : 0.1
        })
    return _effect

bpm = 122.0

mask = stage.Pipeline()
mask.add_stage(current_mask)
mask.add_stage(generative.Selected(keys[ord("M")], min_n=2, max_n=2, stages=[
    #effect_mirror(mode=1),
    
    #effect_glitch(bw=True),

    stage.ShaderStage("common/passthrough.vert", "post/mirror_polar.frag", {
        "uAngleOffset" : var.Const(bpm / 60.0 * 2 * 3.14159265) * time * var.Const(1.0 / (bpm / 8.0)),
        "uSegmentCount" : 6,
    }),

    #stage.ShaderStage("common/passthrough.vert", "common/passthrough.frag", transform=[transform.zrotate(time * _V(2.0))])
]))

mask_shadow = stage.Pipeline()
mask_shadow.add_stage(mask)
mask_shadow.add_stage(stage.ShaderStage("common/passthrough.vert", "common/mask_shadow.frag", {
    "uOffset" : [15, 15],
    "uColor" : [0.0, 0.0, 0.0, 0.5]
}))

foreground = stage.Pipeline()
foreground.add_stage(current_foreground)
foreground.add_stage(generative.Selected(keys[ord("F")], min_n=1, max_n=2, stages=[
    #effect_chromatic_aberration(),
    effect_mirror(),
    effect_slices(),
    effect_scanlines_fine(),
    effect_scanlines_coarse()
]))
foreground.add_stage(stage.MaskStage(mask))

background = stage.Pipeline()
background.add_stage(current_background)
background.add_stage(generative.Selected(keys[ord("B")] | changes["background_effect"], min_n=1, max_n=2, stages=[
    #effect_chromatic_aberration(),
    effect_mirror(),
    effect_slices(),
    effect_scanlines_fine(),
    effect_scanlines_coarse()
]))

pipeline = stage.Pipeline()
pipeline.add_stage(background)
pipeline.add_stage(mask_shadow)
pipeline.add_stage(foreground)
#pipeline.add_stage(mask)

visualapp.run(window, audio, pipeline)

