import imgui
import mido
import traceback
from pyvisual.node.base import Node
from pyvisual.node import dtype
from pyvisual.audio import pulse, util

class MidiDeviceInput(Node):
    class Meta:
        outputs = [
            {"name" : "output", "dtype" : dtype.midi}
        ]

    def __init__(self):
        super().__init__(always_evaluate=True)

        self._device = None
        self.connect(mido.get_input_names()[0])

    def connect(self, device_name):
        try:
            if self._device is not None:
                self._device.close()
            self._device = mido.open_input(device_name)
        except OSError as e:
            self._device = None
            tracepack.print_exc()

    def _evaluate(self):
        if self._device is not None:
            messages = list(self._device.iter_pending())
            if len(messages) == 0 and self.get_output("output").value == []:
                return
            self.set("output", messages)
        else:
            self.set("output", [])

    def _show_custom_ui(self):
        current_device_name = "<none>"
        if self._device is not None:
            current_device_name = self._device.name

        imgui.push_item_width(150)
        if imgui.begin_combo("", current_device_name):
            for device_name in mido.get_input_names():
                is_selected = device_name == current_device_name
                opened, selected = imgui.selectable(device_name, is_selected)
                if opened:
                    self.connect(device_name)
                if is_selected:
                    imgui.set_item_default_focus()
            imgui.end_combo()

def input_property(name):
    def getter(node):
        return node.get(name)
    def setter(node, value):
        node.get_input(name).value = value
    return property(getter, setter)

class MidiValue(Node):
    class Meta:
        inputs = [
            {"name" : "midi", "dtype" : dtype.midi},
            {"name" : "min", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}, "hide" : False},
            {"name" : "max", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}, "hide" : False},
            {"name" : "step", "dtype" : dtype.float, "dtype_args" : {"default" : 0.1}, "hide" : True},
            {"name" : "type", "dtype" : dtype.str, "hide" : True},
            {"name" : "channel", "dtype" : dtype.int, "hide" : True},
            {"name" : "id", "dtype" : dtype.int, "hide" : True},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float},
        ]

    def __init__(self):
        super().__init__()

        self._learning = False
        self._value = 0

    _type = input_property("type")
    _channel = input_property("channel")
    _id = input_property("id")

    def _update_visible_ports(self):
        self.get_port("i_min")["hide"] = self._type == "relative_value"
        self.get_port("i_max")["hide"] = self._type == "relative_value"
        self.get_port("i_step")["hide"] = self._type != "relative_value"

    def _learn_from_message(self, message):
        self._type = None

        if message.type == "control_change":
            # step-wise rotary knobs
            if message.control in (33, 34, 35, 96, 97, 98):
                self._type = "relative_value"
            else:
                self._type = "absolute_value"
        elif message.type == "note_on":
            self._type = "button"

        if self._type:
            message_id = message.control if message.type == "control_change" else message.note
            self._channel = message.channel
            self._id = message_id
            self._update_visible_ports()
            return True
        return False

    def _match_message(self, message):
        if self._type is None:
            return False

        if message.channel != self._channel:
            return False
        message_id = message.control if message.type == "control_change" else message.note
        if message_id != self._id:
            return False

        if self._type == "button":
            return message.type == "note_on"
        if self._type in ("absolute_value", "relative_value"):
            return message.type == "control_change"

        return False

    def _get_message_value(self, message, last_value):
        def absolute_value(alpha):
            return self.get("min") * (1.0 - alpha) + self.get("max") * alpha

        if message.type == "note_on":
            return absolute_value(message.velocity / 127.0)
        if self._type == "relative_value":
            if message.value == 65:
                return last_value + self.get("step")
            elif message.value == 63:
                return last_value - self.get("step")
            else:
                assert False
        if self._type == "absolute_value":
            return absolute_value(message.value / 127.0)

    def _evaluate(self):
        if self._last_evaluated == 0.0:
            self._update_visible_ports()

        midi = self.get("midi")
        if midi is None:
            midi = []

        if self._learning and len(midi) != 0:
            message = midi[-1]
            self._learn_from_message(message)
            self._learning = False
        if not self._type:
            return

        for message in midi:
            if not self._match_message(message):
                continue
            self._value = self._get_message_value(message, self._value)
            self.set("output", self._value)

    def _show_custom_ui(self):
        label = "Learn"
        if self._type:
            label = "Got c=%d i=%d" % (self._channel, self._id)
        if self._learning:
            label = "Use input..."
        if imgui.button(label):
            self._learning = not self._learning

# TODO
# class MidiLed
