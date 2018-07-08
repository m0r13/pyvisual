#!/usr/bin/env python3

import numpy as np
import math
import cv2
import time
import threading
import glob
import random
from glumpy import app, gl, glm, gloo, data
from rendering import stage, primitive, video, var
from rendering.var import _V
from pyo import *

window = app.Window()

X = np.linspace(0.0, 20.0, num=100)
#Y = np.sin(Y)
#points = [ (i / Y.shape[0] * 200, (y+1)*50) for i, y in enumerate(Y) ]

program = gloo.Program(open("data/shader/common/passthrough.vert").read(), open("data/shader/common/color.frag").read(), count=len(X), version="130")
#print(program._uniforms, program._attributes)
#program["iPosition"] = points
#program["uColor"] = [1.0, 0.0, 1.0, 1.0]

class RingBuffer:
    def __init__(self, size):
        self._size = size
        self._index = 0
        self._buffer = np.zeros((size, ), dtype=np.float32)

    def append(self, value):
        self._buffer[self._index] = value
        self._index = (self._index + 1) % self._size

    @property
    def size(self):
        return self._size

    @property
    def first(self):
        return self._buffer[self._index:]

    @property
    def second(self):
        return self._buffer[0:self._index]

class RingBufferRenderer:
    def __init__(self, buf):
        self._buf = buf

    def render(self, mvp, bounds, color=[1.0, 1.0, 1.0, 1.0], y_range=(-1.0, 1.0)):
        x0, y0, x1, y1 = bounds
        cy = (y0 + y1) / 2
        assert len(color) == 4
        y_min, y_max = y_range

        def x(i):
            return x0 + i / (values.shape[0] - 1) * (x1 - x0)
        def y(value):
            rel_value = ((value - y_min) / (y_max - y_min))
            rel_value = min(1.0, max(0.0, rel_value))
            return y0 + (1 - rel_value) * (y1 - y0)

        values = np.concatenate([self._buf.first, self._buf.second], axis=0)
        points = [ (x(i), y(value)) for i, value in enumerate(values) ]

        primitive.draw_lines(points, color, mvp)
        primitive.draw_rect(*bounds, color, mvp)

buf = RingBuffer(100)
mvp = np.eye(4, dtype=np.float32)
buf_renderer = RingBufferRenderer(buf)

device_infos = pa_get_devices_infos()
def device_to_index(name):
    for card, infos in enumerate(device_infos):
        for device, info in infos.items():
            if info["name"] == name:
                return device
    assert False

class AudioAnalyzer:
    def __init__(self):
        self._server = Server(duplex=1)
        self._server.setOutputDevice(device_to_index("pulseout"))
        self._server.setInputDevice(device_to_index("pulsemonitor"))
        self._server = self._server.boot()

        n = Input()

        # Common cutoff frequency control
        freq = Sig(50)
        freq.ctrl([SLMap(10, 5000, "lin", "value", 50)], title="Cutoff Frequency")

        # Three different lowpass filters
        tone = Tone(n, freq)
        butlp = ButLP(n, freq)
        mooglp = MoogLP(n, freq)

        # Interpolates between input objects to produce a single output
        sel = Selector([tone, butlp, mooglp])
        sel.ctrl(title="Filter selector (0=Tone, 1=ButLP, 2=MoogLP)")

        freq2 = Sig(2.5)
        freq2.ctrl([SLMap(1.0, 100, "lin", "value", 2.5)], title="Blah frequency")

        # Displays the spectrum contents of the chosen source
        sp = Spectrum(sel)

        self._beat = ButLP(Abs(sel), freq2)

        threshold = Sig(0.15)
        threshold.ctrl([SLMap(0.0, 1.0, "lin", "value", 0.15)], title="Beat threshold")

        def beat_on():
            print("Beat on!")
        trig_on = TrigFunc(Thresh(self._beat, threshold=0.15, dir=1), beat_on)

        def beat_off():
            print("Beat off!")
        trig_off = TrigFunc(Thresh(self._beat, threshold=0.15, dir=0), beat_off)

        scope = Scope(self._beat)
        scope_threshold = Scope(threshold)

    @property
    def beat_value(self):
        return self._beat.get(False)

    def start(self):
        self._server.start()

audio = AudioAnalyzer()
audio.start()

@window.event
def on_draw(dt):
    app.clock.tick()
    window.clear()

    Y = np.sin(X + time.time() * 5)
   
    w, h = window.get_size()
    #buf.append(np.sin(time.time()))
    buf.append(audio.beat_value)
    
    #buf_renderer.render(mvp, [10, 10, w - 10, h - 10], [0.0, 1.0, 0.0, 1.0], [0.0, 1.0])

    box_height = 200
    buf_renderer.render(mvp, [10, h - box_height - 10, w - 10, h - 10], [0.0, 1.0, 0.0, 1.0], [0.0, 1.0])

@window.event
def on_key_press(symbol, modifiers):
    if symbol == 81:
        window.close()

@window.event
def on_resize(width, height):
    global mvp
    mvp = glm.ortho(0, width, 0, height, -1.0, 1.0)
    glm.scale(mvp, 1.0, -1.0, 1.0)

@window.event
def on_init():
    app.clock.set_fps_limit(30)

app.run()
