#!/usr/bin/env python3

import numpy as np
import math
import cv2
import time
import threading
import glob
import random
from glumpy import app, gl, glm, gloo, data
from pipeline import *
from video import *
import var
from var import _V

window = app.Window()

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

def load_image(path):
    return np.array(Image.open(path)).view(gloo.Texture2D)
images_index = 0
images = [ load_image(path) for path in glob.glob("data/image/tartuvhs/*.jpg")  ]

@window.event
def on_key_press(symbol, modifiers):
    global images_index

    print("Keypress: %s, %s" % (symbol, modifiers))

    # q
    if symbol == 81:
        window.close()
    if symbol == 0x46:
        i = images_index
        while i == images_index:
            i = np.random.randint(0, len(images))
        transition.animate_to(images[i], _V(0.5))
        images_index = i
    if symbol == 68:
        transition.animate_to(None, _V(0.5))

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

transition = TransitionStage("common/passthrough.vert", "transition/test.frag", images[images_index])
#transition.progress = (var.Time().apply(math.sin) + 1) / 2
#transition.progress = 0.5

pipeline = Pipeline()
pipeline.add_stage(transition)

app.run()
