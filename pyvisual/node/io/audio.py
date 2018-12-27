import imgui
import math
from pyvisual.node.base import Node
from pyvisual.node import dtype
from pyvisual.audio import pulse, util

DEFAULT_SAMPLE_RATE = 5000
DEFAULT_BLOCK_SIZE = 64

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
        inputs = [
            {"name" : "samplerate", "dtype" : dtype.int, "dtype_args" : {"default" : 5000}}
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.audio}
        ]
        options = {
            "category" : "audio"
        }

    def __init__(self):
        super().__init__(always_evaluate=True)

        sr = DEFAULT_SAMPLE_RATE
        bs = DEFAULT_BLOCK_SIZE

        self.create(sr, bs)

    def create(self, samplerate, blocksize):
        self.pulse = pulse.PulseAudioContext(self._process_block, sample_rate=samplerate, block_size=blocksize)
        self.output = AudioData(sample_rate=samplerate)
        self.next_blocks = []
        self.blocks = 0

    def _process_block(self, block):
        self.next_blocks.append(block)
        self.blocks += 1

    def start(self, graph):
        self.pulse.start()

    def _evaluate(self):
        samplerate_value = self.get_input("samplerate")
        if samplerate_value.has_changed:
            self.stop()
            sr = int(samplerate_value.value)
            bs = 2 ** int(math.log2(sr / 60.0))
            self.create(sr, bs)
            self.start(None)

        self.output.blocks = self.next_blocks
        self.next_blocks = []
        self.set("output", self.output)

    def stop(self):
        self.pulse.stop()
        self.pulse.join()

    def _show_custom_ui(self):
        imgui.dummy(0, 10)
        imgui.text("Sourced %d blocks" % self.blocks)

        sinks = self.pulse.sinks
        current_sink_index = self.pulse.current_sink_index
        current_sink_name = sinks.get(current_sink_index, "<unknown>")
        #print("Unkown sink %s out of %s" % (repr(current_sink_index), sinks))

        imgui.push_item_width(250)
        if imgui.begin_combo("", current_sink_name):
            for index, sink_name in sinks.items():
                is_selected = index == current_sink_index
                opened, selected = imgui.selectable(sink_name, is_selected)
                if opened:
                    self.pulse.current_sink_index = index
                if is_selected:
                    imgui.set_item_default_focus()
            imgui.end_combo()


