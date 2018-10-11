# TODO naming
import pyvisual.node as node_meta
from pyvisual.node import dtype
import imgui

def clamper(minmax):
    return lambda x: max(minmax[0], (min(minmax[1], x)))

class Int:
    def __init__(self, node, minmax=[float("-inf"), float("inf")]):
        self.node = node
        self.minmax = minmax
        self.clamper = clamper(minmax)

    def show(self, value, read_only):
        imgui.push_item_width(100)
        changed, v = imgui.input_int("", value.value)
        if changed and not read_only:
            value.value = self.clamper(v)

class Choice:
    def __init__(self, node, choices=[]):
        self.node = node
        self.choices = choices

    def show(self, value, read_only):
        imgui.push_item_width(100)
        changed, v = imgui.combo("", value.value, self.choices)
        if changed and not read_only:
            value.value = v

class Float:
    def __init__(self, node, minmax=[float("-inf"), float("inf")]):
        self.node = node
        self.minmax = minmax
        self.clamper = clamper(minmax)

    def show(self, value, read_only):
        imgui.push_item_width(100)
        changed, v = imgui.drag_float("", value.value,
                change_speed=0.01, min_value=self.minmax[0], max_value=self.minmax[1], format="%0.4f")
        if changed and not read_only:
            value.value = self.clamper(v)

class Color:
    def __init__(self, node):
        pass
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
    def __init__(self, node):
        self.node = node
        self.show_texture = False

    def show(self, value, read_only):
        clicked, self.show_texture = imgui.checkbox("Show texture", self.show_texture)
        if not self.show_texture:
            return

        cursor_pos = imgui.get_cursor_screen_pos()
        imgui.set_next_window_size(200, 220, imgui.ONCE)
        imgui.set_next_window_position(*imgui.get_io().mouse_pos, imgui.ONCE, pivot_x=0.5, pivot_y=0.5)
        expanded, opened = imgui.begin("Texture###%s" % id(self.node), True, imgui.WINDOW_NO_SCROLLBAR)
        if not opened:
            self.show_texture = False
        if expanded:
            texture = value.value
            if texture is None:
                imgui.text("No texture associated")
            else:
                # [::-1] reverses list
                texture_size = texture.shape[:2][::-1]
                texture_aspect = texture_size[0] / texture_size[1]
                window_size = imgui.get_content_region_available()
                imgui.image(texture._handle, window_size[0], window_size[0] / texture_aspect)
            imgui.end()

