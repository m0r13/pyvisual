from pyvisual.node.base import Node
from pyvisual.node import dtype
from pyvisual.node.io.audio import AudioData, DEFAULT_SAMPLE_RATE
from pyvisual.node.op.module import Module
from pyvisual.audio import util
from scipy import signal
import math
import time
import numpy as np
import imgui

AUDIO_FILTER_TYPES = ["low", "high"]
class AudioFilter(Node):
    class Meta:
        inputs = [
            {"name" : "enabled", "dtype" : dtype.bool, "dtype_args" : {"default" : True}},
            {"name" : "input", "dtype" : dtype.audio},
            {"name" : "type", "dtype" : dtype.int, "dtype_args" : {"choices" : AUDIO_FILTER_TYPES}},
            {"name" : "order", "dtype" : dtype.int, "dtype_args" : {"default" : 5, "range" : [1, 10]}},
            {"name" : "cutoff", "dtype" : dtype.float, "dtype_args" : {"default" : 1000.0, "range" : [0.0001, float("inf")]}}
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.audio}
        ]
        options = {
            "category" : "audio"
        }

    def __init__(self):
        super().__init__()

        self.filter = None
        # contains error message if there is a problem
        self.filter_status = None
        self.output = None

    def build_filter(self, sample_rate):
        filter_type = int(self.get("type"))
        if not filter_type in (0, 1):
            filter_type = 0
        btype = AUDIO_FILTER_TYPES[filter_type]
        order = self.get("order")
        cutoff = self.get("cutoff")
        try:
            self.filter = util.Filter(signal.butter, order, cutoff, sample_rate, {"btype" : btype, "analog" : False})
            self.filter_status = None
        except ValueError as e:
            self.filter = None
            self.filter_status = str(e)
            self.filter_status += "\n"
            self.filter_status += "\nFilter type: %s" % btype
            self.filter_status += "\nOrder: %f" % order
            self.filter_status += "\nCutoff: %f" % cutoff
            self.filter_status += "\nSamplerate: %f" % sample_rate

    def _evaluate(self):
        input_audio = self.get("input")

        if input_audio is None:
            self.set("output", None)
            return

        if ((self.filter is None or self.output is None) and self.filter_status is None) \
                or self.have_inputs_changed("type", "order", "cutoff") \
                or self.output.sample_rate != input_audio.sample_rate \
                or self._last_evaluated == 0.0:
            self.build_filter(sample_rate=input_audio.sample_rate)
            self.output = AudioData(sample_rate=input_audio.sample_rate)

        if self.filter is None:
            self.set("output", None)
            return

        if not self.get("enabled"):
            self.set("output", input_audio)
            return

        self.output.clear()
        for block in input_audio.blocks:
            self.output.append(self.filter.process(block))
        self.set("output", self.output)

    def _show_custom_ui(self):
        if self.filter_status is not None:
            imgui.dummy(1, 5)
            imgui.text_colored("Filter error. (?)", 1.0, 0.0, 0.0)
            if imgui.is_item_hovered():
                imgui.set_tooltip(self.filter_status)

    def _show_custom_context(self):
        if imgui.button("copy filter coefficients"):
            if self.filter is not None:
                import clipboard
                clipboard.copy("""a = %s\nb = %s""" % (str(self.filter._a.tolist()), str(self.filter._b.tolist())))

class AbsAudio(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.audio}
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.audio},
        ]
        options = {
            "category" : "audio"
        }

    def _evaluate(self):
        input_audio = self.get("input")
        if input_audio is None:
            self.set("output", None)
            return

        output = AudioData(input_audio.sample_rate)
        for block in input_audio.blocks:
            output.append(np.abs(block))
        self.set("output", output)

class SampleAudio(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.audio}
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float},
        ]
        options = {
            "category" : "audio"
        }

    def _evaluate(self):
        input_audio = self.get("input")
        if input_audio is None:
            self.set("output", 0.0)
            return

        if len(input_audio.blocks) == 0:
            return

        block = input_audio.blocks[-1]
        self.set("output", block[-1])

class VUNormalizer(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.float},
            {"name" : "offset", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "beat_on", "dtype" : dtype.bool},
            {"name" : "min", "dtype" : dtype.float, "dtype_args" : {"default" : 0.5}},
            {"name" : "max", "dtype" : dtype.float, "dtype_args" : {"default" : 0.9}},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float}
        ]

    def __init__(self):
        super().__init__()

        self._factor = 1.0

        self._current_max_vu = 0.0
        self._last_vus = []
        self._last_vu_count = 4

    def evaluate(self):
        beat_on = self.get("beat_on")
        vu_norm = (self.get("input") - self.get("offset")) * self._factor
        self.set("output", vu_norm)

        min_vu = self.get("min")
        max_vu = self.get("max")

        # get highest (normalized) vu while beat is on
        if beat_on:
            if self._current_max_vu is None:
                self._current_max_vu = 0.0
            self._current_max_vu = max(self._current_max_vu, vu_norm)

        # once beat turns off...
        if not beat_on and self._current_max_vu is not None:
            self._last_vus.append(self._current_max_vu)
            if len(self._last_vus) >= self._last_vu_count:
                average_vu = sum(self._last_vus) / len(self._last_vus)
                if (average_vu < min_vu or average_vu > max_vu) and average_vu != 0.0:
                    adjust_factor = ((max_vu + min_vu) / 2) / average_vu
                    self._factor *= adjust_factor
                self._last_vus = []
            self._current_max_vu = None

        return vu_norm

def sliding_window_average(n=4):
    window = []
    def _process(value):
        nonlocal window
        window.append(value)
        if len(window) > n:
            window.pop(0)
        return sum(window) / len(window)
    return _process

class BeatAnalyzer(Node):
    class Meta:
        inputs = [
            {"name" : "beat_on", "dtype" : dtype.bool},
        ]
        outputs = [
            {"name" : "beat_running", "dtype" : dtype.bool},
            {"name" : "bpm", "dtype" : dtype.float},
        ]

    def __init__(self):
        super().__init__(always_evaluate=True)

        self.last_beat_on = False

        self.current_bpm = 0.0
        self.is_beat_running = False

        self.last_beat = time.time()
        self.delta_to_last_beat = lambda self=self: time.time() - self.last_beat
        self.bpm_from_last_beat = lambda self=self: 60.0 / self.delta_to_last_beat()

        self.bpm_window_average = sliding_window_average(8)
        self.p = False

    # TODO the whole checking when the beat is running if the
    # bpm with the new beat is within range of current bpm is broken

    # is_beat_running = ...
    def bpm_fits_lower_threshold(self, bpm):
        if not self.is_beat_running or True:
            return bpm > 60.0
        return bpm > self.current_bpm * 0.8
    def bpm_fits_higher_threshold(self, bpm):
        if not self.is_beat_running or True:
            return bpm < 200.0
        return bpm < self.current_bpm * 1.2
    def is_bpm_sensible(self, bpm):
        return self.bpm_fits_lower_threshold(bpm) and self.bpm_fits_higher_threshold(bpm)

    def _evaluate(self):
        beat_on = self.get("beat_on")
        beat_rising = beat_on and not self.last_beat_on
        beat_falling = not beat_on and self.last_beat_on

        if beat_rising:
            bpm = self.bpm_from_last_beat()
            if self.is_bpm_sensible(bpm):
                self.current_bpm = self.bpm_window_average(bpm)
                print("--- bpm", bpm, self.current_bpm, "---")
            else:
                print("hmm, new bpm doesn't make sense:", bpm,)
            self.last_beat = time.time()

        #print(self.bpm_from_last_beat())
        self.is_beat_running = self.bpm_fits_lower_threshold(self.bpm_from_last_beat())
        #print(self.is_beat_running)
        if not self.is_beat_running and not self.p:
            self.bpm_window_average = sliding_window_average(8)
            print("-- emptying avg bpm window --")
            self.p = True
        if self.is_beat_running:
            self.p = False

        self.last_beat_on = beat_on

        self.set("beat_running", self.is_beat_running)
        self.set("bpm", self.current_bpm)

class BeatDetection(Module):
    class Meta:
        pass

    def __init__(self):
        super().__init__("BeatDetection.json")

