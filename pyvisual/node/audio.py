from pyvisual.node.base import Node
from pyvisual.node import dtype
from pyvisual.editor import widget
from pyvisual.audio import pulse, util
from scipy import signal
import numpy as np
import imgui

class AudioData:
    def __init__(self, sample_rate):
        self.blocks = []
        self.sample_rate = sample_rate

    def append(self, block):
        self.blocks.append(block)

    def clear(self):
        self.blocks = []

class InputPulseAudio(Node):
    class Meta:
        outputs = [
            {"name" : "output", "dtype" : dtype.audio, "widgets" : []}
        ]
        options = {
            "category" : "audio"
        }

    def __init__(self):
        super().__init__(always_evaluate=True)

        self.pulse = pulse.PulseAudioContext(self._process_block, sample_rate=5000, block_size=128)
        self.output = AudioData(sample_rate=5000)
        self.next_blocks = []
        self.blocks = 0

    def _process_block(self, block):
        self.next_blocks.append(block)
        self.blocks += 1

    def start(self):
        self.pulse.start()

    def _evaluate(self):
        self.output.blocks = self.next_blocks
        self.next_blocks = []
        self.set("output", self.output)

    def stop(self):
        self.pulse.stop()
        self.pulse.join()

    def _show_custom_ui(self):
        imgui.dummy(0, 10)
        imgui.text("Sourced %d blocks" % self.blocks)

AUDIO_FILTER_TYPES = ["low", "high"]
class AudioFilter(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.audio},
            {"name" : "type", "dtype" : dtype.int, "widgets" : [lambda node: widget.Choice(node, choices=AUDIO_FILTER_TYPES)]},
            {"name" : "order", "dtype" : dtype.int, "widgets" : [lambda node: widget.Int(node, minmax=[1, 10])], "default" : 5},
            {"name" : "cutoff", "dtype" : dtype.float, "widgets" : [lambda node: widget.Float(node, minmax=[0.0, 20000.0])], "default" : 1000.0},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.audio, "widgets" : []}
        ]
        options = {
            "category" : "audio"
        }

    def __init__(self):
        super().__init__()

        self.filter = None
        self.output = None

    def _create_filter(self, sample_rate):
        filter_type = int(self.get("type"))
        if not filter_type in (0, 1):
            filter_type = 0
        btype = AUDIO_FILTER_TYPES[filter_type]
        return util.Filter(signal.butter, self.get("order"), self.get("cutoff"), sample_rate, {"btype" : btype, "analog" : False})

    def _evaluate(self):
        input_audio = self.get("input")
        if input_audio is None:
            self.set("output", None)
            return
        if self.filter is None or self.output is None \
                or any(map(lambda v: v.has_changed, [self.inputs["type"], self.inputs["order"], self.inputs["cutoff"]])) \
                or self.output.sample_rate != input_audio.sample_rate:
            self.filter = self._create_filter(sample_rate=input_audio.sample_rate)
            self.output = AudioData(sample_rate=input_audio.sample_rate)

        self.output.clear()
        for block in input_audio.blocks:
            self.output.append(self.filter.process(block))
        self.set("output", self.output)

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
            {"name" : "output", "dtype" : dtype.float, "widgets" : [widget.Float]},
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

