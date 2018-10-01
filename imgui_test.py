#!/usr/bin/env python3

import sys
from vispy import app, gloo, keys
import imgui, vispy_imgui

canvas = app.Canvas(keys='interactive', vsync=False, autoswap=True)
timer = app.Timer(1.0 / 60.0, connect=canvas.update, start=True)
imgui_renderer = vispy_imgui.GlumpyGlfwRenderer(canvas.native, True)

closed = False

@canvas.connect
def on_draw(event):
    global closed

    gloo.set_clear_color((0.2, 0.4, 0.6, 1.0))
    # TODO why does gloo.clear not work?
    #gloo.clear(depth=True, color=True)
    gloo.gl.glClear(gloo.gl.GL_COLOR_BUFFER_BIT)

    imgui_renderer.process_inputs()
    imgui.new_frame()
    imgui.show_test_window()

    if not closed:
        flags = imgui.WINDOW_NO_RESIZE | imgui.WINDOW_ALWAYS_AUTO_RESIZE
        flags = 0
        expanded, opened = imgui.begin("TestNode", True, flags)
        if expanded:
            imgui.columns(2, "mixed")
            imgui.text("Inputs")
            imgui.next_column()
            imgui.text("Outputs")
            imgui.text("Test!")
            w = imgui.get_window_position()
            imgui.text("My window is at %d:%d" % (w.x, w.y))
            m = imgui.get_cursor_screen_pos()
            imgui.text("I start at %d:%d" % (m.x, m.y))
            imgui.next_column()
        imgui.end()
        if not opened:
            print("was closed!")
            closed = True

    #imgui.set_next_window_position(10, 10, condition=imgui.ALWAYS, pivot_x=0, pivot_y=0)
    #imgui.set_next_window_size(0.0, 0.0)
    #flags = imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_RESIZE + imgui.WINDOW_NO_MOVE + imgui.WINDOW_NO_COLLAPSE

    #imgui.begin("Stats", None, flags)
    #imgui.text("FPS: %.2f" % app.clock.get_fps())
    #imgui.text("Current BPM: %.2f" % current_bpm.value)
    #imgui.text("Beat running: %s" % {True : "Yes", False : "Nope"}[is_beat_running])
    #imgui.end()

    imgui.render()
    draw = imgui.get_draw_data()
    imgui_renderer.render(draw)

@canvas.connect
def on_key_press(event):
    if event.key == "q":
        sys.exit(0)

if __name__ == "__main__":
    canvas.show()
    app.run()
