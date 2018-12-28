import imgui
import time
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
            {"name" : "width", "dtype" : dtype.int, "dtype_args" : {"default" : 200}, "group" : "additional"},
            {"name" : "height", "dtype" : dtype.int, "dtype_args" : {"default" : 50}, "group" : "additional"},
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
        width = int(self.get("width"))
        height = int(self.get("height"))
        imgui.plot_lines("", self.buffer.contents, float(self.get("min")), float(self.get("max")), (width, height))

class BeatMonitor(Node):
    class Meta:
        inputs = [
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
        self._last_beats = None
        self._update_buffers()

    def _update_buffers(self):
        self._duration = self.get("duration")
        self._beat_value_buffer = analyzer.RingBuffer(int(self._duration*60))
        self._last_beats = []

    def _evaluate(self):
        if self.have_inputs_changed("duration"):
            self._update_buffers()

        self._beat_value_buffer.append(self.get("beat_value"))
        if self.get("beat_rising"):
            self._last_beats.append(time.time())

        start_time = time.time() - self._duration
        while len(self._last_beats) and self._last_beats[0] < start_time:
            self._last_beats.pop(0)

    def _show_custom_ui(self):
        width = 250
        height = 100

        draw_list = imgui.get_window_draw_list()
        plot_start = imgui.get_cursor_screen_pos()
        imgui.push_style_color(imgui.COLOR_PLOT_LINES, 0.8, 0.8, 0.8, 1.0)
        imgui.plot_lines("", self._beat_value_buffer.contents, 0.0, 1.0, (width, height))
        imgui.pop_style_color()
        plot_size = imgui.get_item_rect_size()

        t = time.time()
        for abs_time in self._last_beats:
            rel_time = 1.0 - (t - abs_time) / self._duration
            x = width * rel_time
            line_start = plot_start[0] + x, plot_start[1]
            line_end = plot_start[0] + x, plot_start[1] + height
            draw_list.add_line(line_start, line_end, imgui.get_color_u32_rgba(0.0, 0.8, 0.0, 0.8))

        threshold = min(1.0, max(0.0, self.get("threshold")))
        threshold_start = plot_start[0], plot_start[1] + (1.0 - threshold) * height
        threshold_end = plot_start[0] + width, threshold_start[1]

        draw_list.add_line(threshold_start, threshold_end, imgui.get_color_u32_rgba(0.8, 0.0, 0.0, 0.8))
