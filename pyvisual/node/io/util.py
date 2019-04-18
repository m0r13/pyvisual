import imgui
import time
import numpy as np
from pyvisual.node.base import Node
from pyvisual.node import dtype
from pyvisual.audio import analyzer

class Plot(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.float},
            {"name" : "min", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "max", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "time", "dtype" : dtype.float, "dtype_args" : {"default" : 5.0}},
            {"name" : "width", "dtype" : dtype.int, "dtype_args" : {"default" : 300}, "group" : "additional"},
            {"name" : "height", "dtype" : dtype.int, "dtype_args" : {"default" : 100}, "group" : "additional"},
        ]
        options = {
            "category" : "math",
            "virtual" : False
        }

    def __init__(self):
        super().__init__(always_evaluate=True)
        self.buffer = analyzer.RingBuffer(5*60)

    def _evaluate(self):
        self.buffer.append(self.get("input"))

    def _show_custom_ui(self):
        if self.have_inputs_changed("time"):
            t = self.get("time")
            count = int(self.get("time") * 60)
            if count <= 0:
                count = 1
            self.buffer = analyzer.RingBuffer(count)

        width = int(self.get("width"))
        height = int(self.get("height"))
        imgui.plot_lines("", self.buffer.contents, float(self.get("min")), float(self.get("max")), (width, height))

class PlotFFT(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.fft},
            {"name" : "min_freq", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "max_freq", "dtype" : dtype.float, "dtype_args" : {"default" : 22100.0}},
            {"name" : "scale", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "offset", "dtype" : dtype.float},
            {"name" : "width", "dtype" : dtype.int, "dtype_args" : {"default" : 500}, "group" : "additional"},
            {"name" : "height", "dtype" : dtype.int, "dtype_args" : {"default" : 200}, "group" : "additional"},
        ]
        options = {
            "category" : "math",
            "virtual" : False
        }

    def __init__(self):
        super().__init__(always_evaluate=True)

        self._fft = ([], [])

    def _evaluate(self):
        self._fft = self.get("input")

    def _show_custom_ui(self):
        if self._fft is None:
            imgui.text("No fft data!")
            return

        fft = self._fft
        width = int(self.get("width"))
        height = int(self.get("height"))
        min_freq = self.get("min_freq")
        max_freq = self.get("max_freq")

        freq_mask = (fft.frequencies >= min_freq) & (fft.frequencies < max_freq)
        frequencies = fft.frequencies[freq_mask]
        magnitudes = fft.magnitudes[freq_mask]

        imgui.plot_lines("", magnitudes * self.get("scale") + self.get("offset"), 0.0, 1.0, (width, height))
        imgui.text("%d FFT bins: %0.2fHz - %0.2fHz, resolution: %0.2fHz" % (len(frequencies), frequencies[0], frequencies[-1], fft.bin_resolution))

class BeatMonitor(Node):
    class Meta:
        inputs = [
            {"name" : "gain", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "beat_value", "dtype" : dtype.float},
            {"name" : "beat_rising", "dtype" : dtype.event},
            {"name" : "threshold", "dtype" : dtype.float, "dtype_args" : {"default" : 0.5, "range" : [0.0, 1.0]}},
            {"name" : "duration", "dtype" : dtype.float, "dtype_args" : {"default" : 5.0}},
        ]
        options = {
            "category" : "math",
            "virtual" : False
        }

    def __init__(self):
        super().__init__(always_evaluate=True)

        self._duration = 0
        self._beat_value_buffer = None
        self._beat_rising_buffer = None
        self._update_buffers()

    def _update_buffers(self):
        self._duration = self.get("duration")
        self._beat_value_buffer = analyzer.RingBuffer(int(self._duration*60))
        self._beat_rising_buffer = analyzer.RingBuffer(int(self._duration*60))
        self._last_beats = []

    def _evaluate(self):
        if self.have_inputs_changed("duration"):
            self._update_buffers()

        self._beat_value_buffer.append(self.get("beat_value") / self.get("gain"))
        self._beat_rising_buffer.append(self.get("beat_rising"))

    def _show_custom_ui(self):
        width = 250
        height = 100

        draw_list = imgui.get_window_draw_list()
        plot_start = imgui.get_cursor_screen_pos()
        imgui.push_style_color(imgui.COLOR_PLOT_LINES, 0.8, 0.8, 0.8, 1.0)
        imgui.plot_lines("", self._beat_value_buffer.contents * self.get("gain"), 0.0, 1.0, (width, height))
        imgui.pop_style_color()
        plot_size = imgui.get_item_rect_size()

        beat_risings = self._beat_rising_buffer.contents
        count = self._beat_rising_buffer.size
        for i, beat_rising in enumerate(beat_risings):
            if not beat_rising:
                continue
            x = i / (count - 1) * width
            line_start = plot_start[0] + x, plot_start[1]
            line_end = plot_start[0] + x, plot_start[1] + height
            draw_list.add_line(line_start, line_end, imgui.get_color_u32_rgba(0.0, 0.8, 0.0, 0.8))

        threshold = min(1.0, max(0.0, self.get("threshold")))
        threshold_start = plot_start[0], plot_start[1] + (1.0 - threshold) * height
        threshold_end = plot_start[0] + width, threshold_start[1]

        draw_list.add_line(threshold_start, threshold_end, imgui.get_color_u32_rgba(0.8, 0.0, 0.0, 0.8))
