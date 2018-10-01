from glumpy import app, gl, glm, gloo, data, key
from scipy import fftpack
import imgui

from pyvisual.rendering import stage, primitive, transform, video, var, util, glumpy_imgui
from pyvisual.rendering.var import _V
from pyvisual.rendering.generative import *
from pyvisual.event import *
from pyvisual.audio import analyzer

def plot_values(values, mvp, bounds, color=(1.0, 1.0, 1.0, 1.0), bg_color=(0.0, 0.0, 0.0, 0.2), y_range=(-1.0, 1.0)):
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

    #values = np.concatenate([self._buf.first, self._buf.second], axis=0)
    points = [ (x(i), y(value)) for i, value in enumerate(values) ]

    primitive.fill_rect(bounds, bg_color, mvp)
    primitive.draw_lines(points, color, mvp)
    primitive.draw_rect(*bounds, color, mvp)

def plot_bar_values(values, mvp, bounds, color=(1.0, 1.0, 1.0, 1.0), bg_color=(0.0, 0.0, 0.0, 0.2), y_range=(-1.0, 1.0)):
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

    #values = np.concatenate([self._buf.first, self._buf.second], axis=0)
    points = [ (x(i), y(value)) for i, value in enumerate(values) ]

    primitive.fill_rect(bounds, bg_color, mvp)
    
    #low_y = y(0.0)
    #last_x = x(0.0)
    #for px, py in points:
    #    primitive.fill_rect((last_x, py, px, low_y), color, mvp)
    #    last_x = px

    primitive.draw_lines(points, color, mvp)
    primitive.draw_rect(*bounds, color, mvp)

def run(window, audio, pipeline):
    imgui_renderer = glumpy_imgui.GlumpyGlfwRenderer(window._native_window, False)

    render_hud = True

    time = var.RelativeTime()

    current_bpm = var.Const(0.0)
    is_beat_running = False

    # is_beat_running = ...
    def bpm_fits_lower_threshold(bpm):
        if not is_beat_running:
            return float(bpm) > 60.0
        return float(bpm) > float(current_bpm * 0.9)
    def bpm_fits_higher_threshold(bpm):
        if not is_beat_running:
            return float(bpm) < 200.0
        return float(bpm) < float(current_bpm * 1.1)
    def is_bpm_sensible(bpm):
        return bpm_fits_lower_threshold(bpm) and bpm_fits_higher_threshold(bpm)

    last_beat = var.Const(0.0)
    delta_to_last_beat = time - last_beat
    bpm_from_last_beat = var.Const(60.0) / delta_to_last_beat

    def sliding_window_average(n=4):
        window = []
        def _process(value):
            nonlocal window
            window.append(value)
            if len(window) > n:
                window.pop(0)
            return sum(window) / len(window)
        return _process
    bpm_window_average = sliding_window_average(8)

    p = False

    @window.event
    def on_draw(dt):
        nonlocal bpm_window_average, p

        window.clear()

        audio.process()
        if audio.beat_on.value:
            bpm = float(bpm_from_last_beat)
            print(bpm)
            if is_bpm_sensible(bpm):
                current_bpm.value = bpm_window_average(bpm)
                print("--- bpm", bpm, "---")
            else:
                print("hmm?", bpm)
            last_beat.value = float(time)

        is_beat_running = bpm_fits_lower_threshold(bpm_from_last_beat)
        if not is_beat_running and not p:
            bpm_window_average = sliding_window_average(8)
            print("-- empty --")
            p = True
        if is_beat_running:
            p = False

        w, h = window.get_size()
        pipeline.render_screen(None, (w, h))

        if render_hud:
            #print(audio._current_beat_amplitude, audio.vu.value, audio.vu_norm.value)
            #print(audio.vu._evaluated, audio.vu._value)
            color = (0.0, 1.0, 0.0, 1.0)
            bg_color = (0.0, 0.0, 0.0, 0.8)
            box_height = 200
            bounds = (10, h - box_height - 10, w - 10, h - 10)

            threshold_color = (1.0, 0.0, 0.0, 1.0)
            threshold = audio.beat_threshold
            threshold_y = float(var.Const(threshold).map_range(0.0, 1.0, bounds[3], bounds[1]))

            ortho_px = glm.ortho(0, w, 0, h, -1.0, 1.0)
            glm.scale(ortho_px, 1.0, -1.0, 1.0)
            plot_values(audio.beat_values, ortho_px, bounds, color, bg_color,  [0.0, 1.0])
            primitive.draw_line((bounds[0], threshold_y), (bounds[2], threshold_y), threshold_color, ortho_px)

            #fft = audio._current_fft
            #freqs = fftpack.fftfreq(len(fft), d=1.0 / 5000.0)
            #fft = fft[0:len(fft) // 2] * 0.05
            #if len(fft) > 1:
            #    plot_bar_values(fft, ortho_px, (10, 10, w - 10, 210), color, bg_color, [0.0, 1.0])
            #print(freqs)

        imgui_renderer.process_inputs()
        imgui.new_frame()
        imgui.show_test_window()

        imgui.set_next_window_position(10, 10, condition=imgui.ALWAYS, pivot_x=0, pivot_y=0)
        imgui.set_next_window_size(0.0, 0.0)
        flags = imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_RESIZE + imgui.WINDOW_NO_MOVE + imgui.WINDOW_NO_COLLAPSE

        imgui.begin("Stats", None, flags)
        imgui.text("FPS: %.2f" % app.clock.get_fps())
        imgui.text("Current BPM: %.2f" % current_bpm.value)
        imgui.text("Beat running: %s" % {True : "Yes", False : "Nope"}[is_beat_running])
        imgui.end()

        imgui.render()
        imgui_renderer.render(imgui.get_draw_data())

        #print("Resetting:", repr(Event), audio.vu in Event._instances)
        Event.reset_instances()
        GenerativeStage.reset_instances()

        var.ReloadVar.reload_vars()

    @window.event
    def on_key_press(symbol, modifiers):
        nonlocal render_hud

        if symbol == ord("Q"):
            window.close()
        if symbol == key.UP:
            audio.beat_threshold += 0.025 * 0.5
        if symbol == key.DOWN:
            audio.beat_threshold -= 0.025 * 0.5
        if symbol == key.BRACKETRIGHT:
            audio.beat_gain += 0.1
        if symbol == key.SLASH:
            audio.beat_gain -= 0.1
        if symbol == key.F3:
            render_hud = not render_hud

    @window.event
    def on_resize(width, height):
        pass

    @window.event
    def on_init():
        app.clock.set_fps_limit(0)

    @window.event
    def on_close():
        audio.stop()

    audio.start()
    app.run()
