#!/usr/bin/env python3

import numpy as np
import math
import cv2
import time
import threading
from PIL import Image
from glumpy import app, gl, glm, gloo, data
from rendering import stage, transform, video, var

import imgui
from rendering.glumpy_imgui import GlumpyGlfwRenderer

app.use("glfw")
window = app.Window()
impl = None

@window.event
def on_draw(dt):
    app.clock.tick()
    window.clear()

    impl.process_inputs()

    imgui.new_frame()
    imgui.show_test_window()

    imgui.render()
    impl.render(imgui.get_draw_data())

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
    global impl

    app.clock.set_fps_limit(30)
    # TODO receive callbacks and forward them to glfw backend
    impl = GlumpyGlfwRenderer(window._native_window, False)

app.run()
