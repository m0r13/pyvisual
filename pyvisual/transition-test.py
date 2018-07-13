#!/usr/bin/env python3

import numpy as np
import math
import cv2
import time
import threading
import glob
import random
from glumpy import app, gl, glm, gloo, data
from rendering import stage, var
from rendering.var import _V
from PIL import Image

window = app.Window()

def adjust_shader(shader):
    shader = shader.replace("progress", "uAlpha")
    shader = shader.replace("uniform vec2 resolution;", "uniform sampler2D uInputTexture;in vec2 TexCoord0;out vec4 oFragColor;")
    shader = shader.replace("from", "uTexture1")
    shader = shader.replace("to", "uTexture2")
    shader = shader.replace("gl_FragCoord.xy/resolution.xy", "TexCoord0")
    shader = shader.replace("resolution", "textureSize(uInputTexture, 0)")
    shader = shader.replace("gl_FragColor", "oFragColor")
    for c in ";{}":
        shader = shader.replace(c, c + "\n")
    return shader
def adjust_uniform_value(value):
    if isinstance(value, list):
        return np.array(value, np.float32)
    return value

import json
transitions_index = 0
transitions = []
update_transitions = False
for shader in json.load(open("data/shader/transition/glsl-transition/shaders.json")):
    transition = {
        "name" : shader["name"],
        "uniforms" : { key:adjust_uniform_value(value) for key, value in shader["uniforms"].items() },
        "glsl" : adjust_shader(shader["glsl"])
    }
    transitions.append(transition)
transitions = [dict(name="test", uniforms={}, glsl="transition/test.frag")]
print("Loaded %d transition effects" % len(transitions))

def load_image(path):
    return np.array(Image.open(path)).view(gloo.Texture2D)
images_index = 0
images = [ load_image(path) for path in glob.glob("data/image/tartuvhs/*.jpg")  ]

@window.event
def on_draw(dt):
    global update_transitions

    app.clock.tick()
    window.clear()

    gl.glEnable(gl.GL_BLEND);
    gl.glBlendEquationSeparate(gl.GL_FUNC_ADD, gl.GL_FUNC_ADD);
    gl.glBlendFuncSeparate(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA, gl.GL_ONE, gl.GL_ONE_MINUS_SRC_ALPHA);

    if update_transitions:
        transition.set_shader("common/passthrough.vert", transitions[transitions_index]["glsl"])
        update_transitions = False

    w, h = window.get_size()
    #print("----------")
    pipeline.render_screen(None, (w, h))
    var.ReloadVar.reload_vars()

@window.event
def on_key_press(symbol, modifiers):
    global transitions_index
    global update_transitions
    global images_index

    print("Keypress: %s, %s" % (symbol, modifiers))

    # q
    if symbol == 81:
        window.close()
    

    update_transition = True
    # k
    if symbol == 75:
        transitions_index = (transitions_index - 1) % len(transitions)
    # l
    elif symbol == 76:
        transitions_index = (transitions_index + 1) % len(transitions)
    else:
        update_transition = False
    if update_transition:
        print("Loading transition #%d: %s" % (transitions_index, transitions[transitions_index]["name"]))
        print("Uniforms: %s" % (transitions[transitions_index]["uniforms"]))
        print("---")
        print(transitions[transitions_index]["glsl"])
        print("---")
        update_transitions = True

    next_image = None
    if symbol == 44:
        images_index = (images_index - 1) % len(images)
        next_image = images[images_index]
    elif symbol == 46:
        images_index = (images_index + 1) % len(images)
        next_image = images[images_index]
    elif symbol == 0x46:
        i = images_index
        while i == images_index:
            i = np.random.randint(0, len(images))
        images_index = i
        next_image = images[i]
    elif symbol == 68:
        next_image = None
    else:
        return
    transition.animate_to(next_image, _V(1.0))

@window.event
def on_resize(width, height):
    pass

@window.event
def on_init():
    app.clock.set_fps_limit(30)

img1 = np.array(Image.open("data/image/1.jpg")).view(gloo.Texture2D)
img2 = np.array(Image.open("data/image/2.jpg")).view(gloo.Texture2D)

transition_img1 = img1
transition_img2 = img2
#
#strength = var.ReloadVar(0.5)
#def config_program(program):
#    program["uTexture2"] = transition_img2
#    program["uAlpha"] = (var.Time().apply(math.sin) + 1) / 2
#    program["strength"] = float(strength)
#
#texture_stage = TextureStage(transition_img1)

#pipeline = Pipeline()
#pipeline.add_stage(texture_stage)
#pipeline.add_stage(ShaderStage("common/passthrough.vert", "transition/test.frag", config_program))

transition = stage.TransitionStage("common/passthrough.vert", transitions[transitions_index]["glsl"], images[images_index])
#transition.progress = (var.Time().apply(math.sin) + 1) / 2
#transition.progress = 0.5

pipeline = stage.Pipeline()
pipeline.add_stage(transition)

app.run()
