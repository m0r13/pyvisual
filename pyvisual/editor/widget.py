import node_meta
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

class ImGuiFloat(ImGuiValue):
    def show(self, value, read_only):
        imgui.push_item_width(100)
        changed, v = imgui.drag_float("", value.value, change_speed=0.01)
        if changed and not read_only:
            value.value = v

