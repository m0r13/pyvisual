# TODO naming
import pyvisual.node as node_meta
from pyvisual.node import dtype
import imgui

class ImGuiValue:
    def __init__(self):
        pass

    def show(self, value, read_only=False):
        pass

    @staticmethod
    def create(port_spec):
        if port_spec["dtype"] == dtype.float:
            return ImGuiFloat()
        if port_spec["dtype"] == dtype.vec4:
            return ImGuiColor()
        if port_spec["dtype"] == dtype.tex2d:
            return ImGuiTexture()

class ImGuiFloat(ImGuiValue):
    def show(self, value, read_only):
        imgui.push_item_width(100)
        changed, v = imgui.drag_float("", value.value, change_speed=0.01)
        if changed and not read_only:
            value.value = v

class ImGuiColor(ImGuiValue):
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

class ImGuiTexture(ImGuiValue):
    def show(self, value, read_only):
        imgui.text("Widget coming soon")
