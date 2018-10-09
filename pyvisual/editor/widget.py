# TODO naming
import pyvisual.node as node_meta
import imgui

class ImGuiValue:
    def __init__(self):
        pass

    def show(self, value, read_only=False):
        pass

    @staticmethod
    def create(port_spec):
        if port_spec["dtype"] == "float":
            return ImGuiFloat()
        if port_spec["dtype"] == "vec4":
            return ImGuiColor()
        if port_spec["dtype"] == "tex2d":
            return ImGuiTexture()

class ImGuiFloat(ImGuiValue):
    def show(self, value, read_only):
        imgui.push_item_width(100)
        changed, v = imgui.drag_float("", value.value, change_speed=0.01)
        if changed and not read_only:
            value.value = v

class ImGuiColor(ImGuiValue):
    def show(self, value, read_only):
        imgui.text("Widget coming soon")

class ImGuiTexture(ImGuiValue):
    def show(self, value, read_only):
        imgui.text("Widget coming soon")
