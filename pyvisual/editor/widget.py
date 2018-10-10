# TODO naming
import pyvisual.node as node_meta
from pyvisual.node import dtype
import imgui

def clamper(minmax):
    return lambda x: max(minmax[0], (min(minmax[1], x)))

class Int:
    def __init__(self, minmax=[float("-inf"), float("inf")]):
        self.minmax = minmax
        self.clamper = clamper(minmax)

    def show(self, value, read_only):
        imgui.push_item_width(100)
        changed, v = imgui.input_int("", value.value)
        if changed and not read_only:
            value.value = self.clamper(v)

class Choice:
    def __init__(self, choices=[]):
        self.choices = choices

    def show(self, value, read_only):
        imgui.push_item_width(100)
        changed, v = imgui.combo("", value.value, self.choices)
        if changed and not read_only:
            value.value = v

class Float:
    def __init__(self, minmax=[float("-inf"), float("inf")]):
        self.minmax = minmax
        self.clamper = clamper(minmax)

    def show(self, value, read_only):
        imgui.push_item_width(100)
        changed, v = imgui.drag_float("", value.value,
                change_speed=0.01, min_value=self.minmax[0], max_value=self.minmax[1], format="%0.4f")
        if changed and not read_only:
            value.value = self.clamper(v)

class Color:
    def show(self, value, read_only):
        r, g, b, a = value.value[:]
        flags = imgui.COLOR_EDIT_NO_INPUTS | imgui.COLOR_EDIT_NO_LABEL | imgui.COLOR_EDIT_ALPHA_PREVIEW
        if imgui.color_button("color", r, g, b, a, flags, 50, 50):
            imgui.open_popup("picker")
        if imgui.begin_popup("picker"):
            changed, color = imgui.color_picker4("color", r, g, b, a, imgui.COLOR_EDIT_ALPHA_PREVIEW)
            if changed:
                if not read_only:
                    value.value[:] = color
            imgui.end_popup()

class Texture:
    def show(self, value, read_only):
        imgui.text("Widget coming soon")

