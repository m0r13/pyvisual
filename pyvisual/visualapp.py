from glumpy import app, gl, glm, gloo, data, key
from scipy import fftpack

from pyvisual.rendering import stage, primitive, transform, video, var, util
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
    app.use("glfw")

    render_hud = True

    @window.event
    def on_draw(dt):
        app.clock.tick()
        window.clear()

        audio.process()

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

            fft = audio._current_fft
            freqs = fftpack.fftfreq(len(fft), d=1.0 / 5000.0)
            fft = fft[0:len(fft) // 2] * 0.05
            plot_bar_values(fft, ortho_px, (10, 10, w - 10, 210), color, bg_color, [0.0, 1.0])
            #print(freqs)

        #print("Resetting:", repr(Event), audio.vu in Event._instances)
        Event.reset_instances()
        GenerativeStage.reset_instances()

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
        app.clock.set_fps_limit(30)

    audio.start()
    app.run()
