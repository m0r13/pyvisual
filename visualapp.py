from glumpy import app, gl, glm, gloo, data, key
from rendering import stage, transform, video, var, util
from rendering.generative import *

def run(window, pipeline):
    app.use("glfw")

    @window.event
    def on_draw(dt):
        app.clock.tick()
        window.clear()

        w, h = window.get_size()
        pipeline.render_screen(None, (w, h))

        Event.reset_instances()
        GenerativeStage.reset_instances()

    @window.event
    def on_key_press(symbol, modifiers):
        if symbol == ord("Q"):
            window.close()

    @window.event
    def on_resize(width, height):
        pass

    @window.event
    def on_init():
        app.clock.set_fps_limit(30)

    app.run()
