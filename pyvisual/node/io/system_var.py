import json
import os
import time
from collections import defaultdict, OrderedDict

import imgui
from pyvisual.node import dtype, value
from pyvisual.node.base import Node
from pyvisual.editor import widget

SERIALIZATION_WRITE_INTERVAL = 5.0
SERIALIZATION_FILE = "system_vars.json"

# if you add another variable with another dtype than here, add the name of the dtype below!
VARIABLES = OrderedDict([
    ("gain", {"dtype" : dtype.float, "dtype_args" : {"default" : 4.0, "range" : [0.0, float("inf")]}}),
    ("threshold", {"dtype" : dtype.float, "dtype_args" : {"default" : 0.4, "range" : [0.0, float("inf")]}}),
    ("ref_aspect", {"dtype" : dtype.str, "dtype_args" : {"default" : "16:9"}}),
    ("ref_highres_height", {"dtype" : dtype.int, "dtype_args" : {"default" : 1080, "range" : [0, float("inf")]}}),
    ("ref_lowres_height", {"dtype" : dtype.int, "dtype_args" : {"default" : 720, "range" : [0, float("inf")]}}),
    ("ref_noiseres_height", {"dtype" : dtype.int, "dtype_args" : {"default" : 512, "range" : [0, float("inf")]}}),
])

# name -> value for each variable
values = OrderedDict()
# name -> widget for each variable
widgets = OrderedDict()
# dtype -> list of (name, value)
values_by_dtype = defaultdict(lambda: [])

# initialize values and widgets that are associated with variables
for name, spec in VARIABLES.items():
    assert "dtype" in spec

    dt = spec["dtype"]
    dt_args = spec.get("dtype_args", {})
    default_value = dt.default
    if "default" in dt_args:
        default_value = dt_args["default"]

    v = value.SettableValue(default_value)
    w = widget.create_widget(dt, dt_args)
    w.width = widget.WIDGET_WIDTH * 1.5

    values[name] = v
    values_by_dtype[dt].append((name, v))
    widgets[name] = w

_variables_dirty = False
_variables_last_written = 0
_node_instances = set()

# Important: Call this when changed a value! (Is done by editor for example)
def notify_change():
    global _variables_dirty
    _variables_dirty = True

    for instance in _node_instances:
        instance.force_evaluate()
    
    # if the nodes would take over the values if they are changed only,
    # then this would need to be changed probably
    for value in values.values():
        value.reset_changed()

def read_variables():
    serialized_values = {}
    if not os.path.isfile(SERIALIZATION_FILE):
        return

    serialized_values = json.load(open(SERIALIZATION_FILE))
    for name, serialized_value in serialized_values.items():
        if name not in VARIABLES:
            continue
        value = values[name]
        dt = VARIABLES[name]["dtype"]

        value.value = dt.base_type.unserialize(serialized_values[name])
    notify_change()
read_variables()

def write_variables(force=False):
    global _variables_dirty, _variables_last_written

    if force or time.time() - _variables_last_written > SERIALIZATION_WRITE_INTERVAL:
        _variables_dirty = False
        _variables_last_written = time.time()

        data = {}
        for name, spec in VARIABLES.items():
            value = values[name].value
            data[name] = spec["dtype"].base_type.serialize(value)
        with open("system_vars.json", "w") as f:
            json.dump(data, f)

class GetSystemVar(Node):

    DTYPE = None

    class Meta:
        inputs = [
            {"name" : "name", "dtype" : dtype.str, "hide" : True}
        ]
        options = {
            "virtual" : True
        }

    def __init__(self):
        super().__init__()

        self._value = None

    @property
    def collapsed_node_title(self):
        return "get system var: %s" % self.get("name")

    def start(self, graph):
        _node_instances.add(self)

        name = self.get("name")
        if name:
            self._value = values.get(name, None)
            if self._value is None:
                self.get_input("name").value = ""

    def _evaluate(self):
        output = self.get_output("output")
        if self._value != None:
            output.value = self._value.value

    def stop(self):
        _node_instances.remove(self)

    def _show_custom_ui(self):
        selected_name = self.get("name")
        preview = selected_name if selected_name else "<none>"
        if imgui.begin_combo("", preview):
            is_selected = not selected_name
            opened, selected = imgui.selectable("<none>", is_selected)
            if opened:
                self.get_input("name").value = ""
                self._value = None
            if is_selected:
                imgui.set_item_default_focus()
            imgui.separator()

            for name, value in values_by_dtype.get(self.DTYPE, []):
                is_selected = name == selected_name
                opened, selected = imgui.selectable(name, is_selected)
                if opened:
                    self.get_input("name").value = name
                    self._value = value
                if is_selected:
                    imgui.set_item_default_focus()
            imgui.end_combo()

    @classmethod
    def get_presets(cls, graph):
        presets = []
        for name, value in values_by_dtype.get(cls.DTYPE, []):
            presets.append((name, {"i_name" : name}))
        return presets

dtype_capital_names = {
    dtype.float : "Float",
    dtype.str : "Str",
    dtype.int : "Int",
}

# create a GetXXXSystemVar class for each dtype
node_classes = []
for dt in values_by_dtype.keys():
    name = "Get%sSystemVar" % dtype_capital_names[dt]

    class Meta:
        outputs = [
            {"name" : "output", "dtype" : dt, "manual_input": True},
        ]
        options = {
            "virtual" : False,
            "show_title" : False
        }

    cls = type(name, (GetSystemVar,), {"DTYPE" : dt, "Meta" : Meta, "__module__" : __name__})
    node_classes.append(cls)

