#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import math
import logging
from glumpy import app, gl, glm, gloo, data, key
from glumpy.ext import glfw

from pyvisual.rendering import stage, transform, video, var, util
from pyvisual.rendering.var import _V
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
    stage.TextureStage(util.load_texture(name)) for name in util.glob_textures("vapor/*/*.jpg")
])

current_foreground = Iterated(key_right | changes["foreground"] | changes["foreground_completely"], shuffle=True, stages=[
    stage.TextureStage(util.load_texture(name)) for name in util.glob_textures("vapor/*/*.jpg")
])
#current_foreground = current_background

scale = var.Time().apply(lambda x: math.sin(x)).map_range(-1, 1, 0.5, 0.9)
scale = vu_norm.map_range(0.0, 1.0, 0.5, 0.9)

def mask_transition(*args):
    vertex = "common/passthrough.vert"
    fragment = "transition/move.frag"
    uniforms = {}
    duration = 0.5

    return vertex, fragment, uniforms, duration

current_mask = Transitioned(Iterated(key_space | changes["mask"] | changes["foreground_completely"], shuffle=True, stages=[
    stage.TextureStage(util.load_texture(name), transform=[transform.scale(scale)], force_size=(1920, 1080)) for name in util.glob_textures("mask/common/*.png")
]), transition_config=mask_transition)

def effect_mirror(mode=None):
    def _effect(*args):
        m = mode
        if m is None:
            m = np.random.randint(low=0, high=4)
        effect = stage.Pipeline()
        if m == 3:
            # horizontal and vertical mirrored
            angle = math.radians(np.random.randint(low=0, high=7) * 45.0)
            effect.add_stage(stage.ShaderStage("common/passthrough.vert", "post/move.frag", {"uDirection" : angle, "uDirectionOffset" : time * 25.0}))
        effect.add_stage(stage.ShaderStage("common/passthrough.vert", "post/mirror.frag", {"uMode" : m}))
        return effect
    return _effect

def effect_chromatic_aberration():
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
        return stage.ShaderStage("common/passthrough.vert", "post/chromaticaberration.frag", uniforms)
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

def effect_scanlines_fine():
    def _effect(*args):
        return stage.ShaderStage("common/passthrough.vert", "post/scanline.frag", {
            "time" : time,
            "count" : 400.0,
            "noiseAmount" : 0.25,
            "linesAmount" : 0.25
        })
    return _effect

def effect_scanlines_coarse():
    def _effect(*args):
        return stage.ShaderStage("common/passthrough.vert", "post/scanlinescoarse.frag", {
            "uNoiseTexture" : util.load_texture("noise3.png"),
            "time" : time
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
    stage.ShaderStage("common/passthrough.vert", "common/passthrough.frag", transform=[transform.zrotate(var.Time() * 10.0 * 0)]),
    #effect_mirror(mode=3),
    
    #effect_glitch(bw=True)

    #stage.ShaderStage("common/passthrough.vert", "post/mirror_polar.frag", {
    #    "uAngleOffset" : time * 0.25,
    #    "uSegmentCount" : 3,
    #})
]))

mask_shadow = stage.Pipeline()
mask_shadow.add_stage(mask)
mask_shadow.add_stage(stage.ShaderStage("common/passthrough.vert", "common/mask_shadow.frag", {
    "uOffset" : [15, 15],
    "uColor" : [0.0, 0.0, 0.0, 0.5]
}))

foreground = stage.Pipeline()
foreground.add_stage(current_foreground)
foreground.add_stage(Selected(keys[ord("F")], min_n=1, max_n=2, stages=[
    #effect_chromatic_aberration(),
    effect_mirror(),
    effect_slices(),
    effect_scanlines_fine(),
    effect_scanlines_coarse()
]))
foreground.add_stage(stage.MaskStage(mask))

background = stage.Pipeline()
background.add_stage(current_background)
background.add_stage(Selected(keys[ord("B")] | changes["background_effect"], min_n=1, max_n=2, stages=[
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

visualapp.run(window, audio, pipeline)

