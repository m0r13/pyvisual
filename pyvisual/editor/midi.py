import imgui
import mido

class MidiControllerMapping:
    def learn(self, message):
        return None

on_hold = "on_hold", lambda node, value: node.set_relative_value(value)
off_hold = "off_hold", lambda node, value: node.set_relative_value(1.0 - value)
toggle = "toggle", lambda node, value: node.set_relative_value(1.0 - node.get_relative_value()) if value else None
on_once = "on_once", lambda node, value: node.set_relative_value(value) if value else None
abs_value = "abs_value", lambda node, value: node.set_relative_value(value)
rel_value = "rel_value", lambda node, value: node.set_offset_value(value)

class ControllerInput:
    def __call__(self, message):
        # check if the message is the assigned input on the controller and return a value (0...1 usually)
        return None

class ControllerButton(ControllerInput):
    def __init__(self, channel, note):
        self._channel = channel
        self._note = note

    def __call__(self, message):
        if message.type not in ("note_on", "note_off") \
                or message.channel != self._channel \
                or message.note != self._note:
            return None
        return 1.0 if message.velocity > 0 else 0.0

class ControllerAbsoluteKnob(ControllerInput):
    def __init__(self, channel, control):
        self._channel = channel
        self._control = control

    def __call__(self, message):
        if message.type != "control_change" \
                or message.channel != self._channel \
                or message.control != self._control:
            return None
        return message.value / 127.0

class ControllerRelativeKnob(ControllerInput):
    def __init__(self, channel, control):
        self._channel = channel
        self._control = control

    def __call__(self, message):
        if message.type != "control_change" \
                or message.channel != self._channel \
                or message.control != self._control \
                or message.value not in (63, 65):
            return None
        return -1.0 if message.value == 63 else 1.0

class ZomoControllerMapping:
    def learn(self, learning_message):
        channel = learning_message.channel
        if learning_message.type == "note_on":
            return ControllerButton(channel=channel, note=learning_message.note), [on_hold, off_hold, toggle, on_once]
        if learning_message.type == "control_change":
            control = learning_message.control
            if control in (33, 34, 35, 96, 97, 98):
                return ControllerRelativeKnob(channel=channel, control=control), [rel_value]
            else:
                return ControllerAbsoluteKnob(channel=channel, control=control), [abs_value]
        return None, []

def learn_midi_message(message):
    mapping_type = None
    if message.type == "control_change":
        # step-wise rotary knobs
        if message.control in (33, 34, 35, 96, 97, 98):
            mapping_type = "relative_value"
        else:
            mapping_type = "absolute_value"
    elif message.type == "note_on":
        mapping_type = "button"

    if mapping_type:
        message_id = message.control if message.type == "control_change" else message.note
        return {"type" : mapping_type, "channel" : message.channel, "id" : message_id}
    return None

class BehaviorWrapper:
    def __init__(self, behavior_tuples, index=0):
        self._behaviors = [ behavior for label, behavior in behavior_tuples ]
        self._labels = [ label for label, behavior in behavior_tuples ]
        self._index = index
        if self._index < 0 or self._index >= len(self._behaviors):
            self._index = 0

    @property
    def index(self):
        return self._index

    @property
    def behavior(self):
        return self._behaviors[self._index]

    @property
    def label(self):
        return self._labels[self._index]

    def show(self):
        changed, index = imgui.combo("", self._index, self._labels)
        if changed:
            self._index = index

class MidiIntegration:
    # handle midi things only every few frames to improve performance
    CHECK_EVERY_FRAMES = 5
    def __init__(self, device_name):
        self._device_name = device_name
        self._in_device = mido.open_input(device_name)
        self._out_device = mido.open_output(device_name)

        self._check_counter = 0
        self._learning_node = None

        # a mapping is: (midi channel, midi message id) -> (node, mapping params)
        # mapping must be stored somehow
        self._midi_mappings = {}
        # reverse: node -> midi channel
        self._mapped_nodes = {}
        # mapping of new nodes must be retrieved

        self._controller_mapping = ZomoControllerMapping()

        # midi matching function -> node
        self._mappings = {}
        # node -> midi matching function
        self._reverse_mappings = {}
        # midi matching function -> current behavior
        self._midi_behaviors = {}

        # learned message -> node
        self._learn_messages = {}

        self._ignore_once = set()

        # counter to handle midi messages only every N frames
        self._counter = 0

        # assumptions: the message to learn each input button/knob does not change

    @property
    def device_name(self):
        return self._device_name

    @property
    def learning_node(self):
        return self._learning_node

    def _set_mapping(self, node, mapping):
        midi_id = (mapping["channel"], mapping["id"])
        mapping_args = mapping

        print("Setting mapping: %s -> %s" % (str(mapping), node))
        node.midi_mapping = mapping
        self._midi_mappings[midi_id] = (node, mapping_args)
        self._mapped_nodes[node] = midi_id

    def handle(self, nodes):
        self._counter += 1
        if (self._counter % 3) != 0:
            return
        self._counter = 0

        for node in nodes:
            if not node.name:
                continue

            mapping = node.midi_mapping
            if mapping is None or node in self._reverse_mappings:
                continue

            # node has a serialized mapping but is not known to the midi handler yet
            # (= node was not mapped in this session, but deserialized)

            message_hex, behavior_index = mapping

            message = mido.Message.from_hex(message_hex)
            match_message, behaviors = self._controller_mapping.learn(message)
            assert match_message is not None
 
            self._mappings[match_message] = node
            self._reverse_mappings[node] = match_message
            self._midi_behaviors[match_message] = BehaviorWrapper(behaviors, index=behavior_index)
            self._learn_messages[message_hex] = node

        for node in nodes:
            if not node.name:
                continue

            if node.midi_mapping is None:
                continue

            match_message = self._reverse_mappings.get(node, None)
            if match_message is None or not isinstance(match_message, ControllerButton):
                continue

            channel, note = match_message._channel, match_message._note
            self._out_device.send(mido.Message("note_on", channel=channel, note=note, velocity=bool(node.get_relative_value()) * 127))
            self._ignore_once.add(match_message)

        messages = list(self._in_device.iter_pending())
        for message in messages:
            if self._learning_node is not None:
                node = self._learning_node
                match_message, behaviors = self._controller_mapping.learn(message)
                if match_message is not None:
                    behaviors = BehaviorWrapper(behaviors)
                    message_hex = message.hex()
                    if message_hex in self._learn_messages:
                        self.remove_mapping(self._learn_messages[message_hex])
                        del self._learn_messages[message_hex]
                    if node in self._reverse_mappings:
                        self.remove_mapping(node)
                    node.midi_mapping = message_hex, behaviors._index
                    self._mappings[match_message] = node
                    self._reverse_mappings[node] = match_message
                    self._midi_behaviors[match_message] = behaviors
                    self._learn_messages[message_hex] = node
                    self._learning_node = None
                    continue

            for match_message, node in self._mappings.items():
                midi_value = match_message(message)
                if midi_value is None:
                    continue
                #if match_message in self._ignore_once:
                #    self._ignore_once.remove(match_message)
                #    continue
                behaviors = self._midi_behaviors[match_message]
                midi_mapping = node.midi_mapping
                if behaviors._index != midi_mapping[1]:
                    node.midi_mapping = (midi_mapping[0], behaviors._index)
                set_value = behaviors.behavior
                set_value(node, midi_value)

                if isinstance(match_message, ControllerButton):
                    channel, note = match_message._channel, match_message._note
                    self._out_device.send(mido.Message("note_on", channel=channel, note=note, velocity=bool(node.get_output("output").value) * 127))
                    self._ignore_once.add(match_message)
                break

        #self._check_counter += 1
        #if self._check_counter >= self.CHECK_EVERY_FRAMES:
        #    self._check_counter = 0
        #    for node in nodes:
        #        if not node.name:
        #            continue
        #        mapping = node.midi_mapping
        #        if mapping is None:
        #            continue
        #        if node not in self._mapped_nodes:
        #            self._set_mapping(node, mapping)

        #        # doesn't work because we get some messages back that mess up learning
        #        #if mapping["type"] == "button":
        #        #    channel, note = mapping["channel"], mapping["id"]
        #        #    self._out_device.send(mido.Message("note_on", channel=channel, note=note, velocity=bool(node.get_output("output").value) * 127))

        #messages = list(self._in_device.iter_pending())

        #learning = self._learning_node is not None
        #for message in messages:
        #    message_id = message_id = message.control if message.type == "control_change" else message.note
        #    midi_id = (message.channel, message_id)

        #    print("MIDI Message: type=%s, channel=%02x, id=%02x" % (message.type, message.channel, message_id))

        #    if learning:
        #        mapping = learn_midi_message(message)
        #        if mapping is not None:
        #            if midi_id in self._midi_mappings:
        #                self.remove_mapping(self._midi_mappings[midi_id][0])
        #            self.remove_mapping(self._learning_node)
        #            self._set_mapping(self._learning_node, mapping)
        #            self._learning_node = None
        #            # not really necessary probably
        #            learning = False
        #        continue

        #    if midi_id not in self._midi_mappings:
        #        continue

        #    node, mapping_args = self._midi_mappings[midi_id]

        #    mapping_type = mapping_args["type"]
        #    if mapping_type == "button" and message.type != "note_on":
        #        continue
        #    if mapping_type in ("absolute_value", "relative_value") and message.type != "control_change":
        #        continue

        #    if message.type == "note_on":
        #        #return absolute_value(message.velocity / 127.0)
        #        alpha = message.velocity / 127.0
        #        node.set_relative_value(alpha)
        #        #self._out_device.send(mido.Message("note_on", channel=message.channel, note=message_id, velocity=int(alpha * 127)))
        #    if mapping_type == "relative_value":
        #        if message.value == 65:
        #            #return last_value + self.get("step")
        #            node.set_offset_value(1)
        #        elif message.value == 63:
        #            #return last_value - self.get("step")
        #            node.set_offset_value(-1)
        #        else:
        #            assert False
        #    if mapping_type == "absolute_value":
        #        #return absolute_value(message.value / 127.0)
        #        node.set_relative_value(message.value / 127.0)

    def begin_learning(self, node):
        # register node for mapping
        # perform mapping where events are handled

        self._learning_node = node

    def abort_learning(self, node):
        self._learning_node = None

    def remove_mapping(self, node):
        # remove mapping internally

        # reset mapping for node
        #mapping = node.midi_mapping
        #if mapping is not None:
        #    node.midi_mapping = None
        #if node in self._mapped_nodes:
        #    del self._mapped_nodes[node]

        node.midi_mapping = None
        if node in self._reverse_mappings:
            match_message = self._reverse_mappings[node]
            del self._mappings[match_message]
            del self._reverse_mappings[node]
            del self._midi_behaviors[match_message]

