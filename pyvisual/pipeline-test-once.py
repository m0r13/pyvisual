#!/usr/bin/env python3

from glumpy import app

from pipeline import *
from video import *

window = app.Window()
window.hide()

video = VideoReader("/home/moritz/Videos/RickRoll.mp4")
video.time = 20
video.paused = True
video.start()

pipeline = Pipeline()
pipeline.add_stage(VideoStage(video))

texture = pipeline.render_texture(None).get()
Image.fromarray(texture, "RGBA").save("rick.png")

window.close()

