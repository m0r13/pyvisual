# TODO naming
import os
import pyvisual.node as node_meta
from pyvisual.node import dtype
from pyvisual import assets
import time
import imgui

def clamper(minmax):
    return lambda x: max(minmax[0], (min(minmax[1], x)))

# TODO read-only widgets!

class Bool:
    def __init__(self, node):
        pass

    def show(self, value, read_only):
        clicked, state = imgui.checkbox("", value.value)
        if not read_only:
            value.value = state

class Button:
    ACTIVE_TIME = 0.1
    def __init__(self, node):
        self.last_active = 0

    def show(self, value, read_only):
        imgui.push_item_width(100)
        active = value.value or time.time() - self.last_active < Button.ACTIVE_TIME
        if value.value:
            self.last_active = time.time()
        imgui.push_style_color(imgui.COLOR_BUTTON_ACTIVE, 1.0, 0.0, 0.0, 1.0)
        if active:
            imgui.push_style_color(imgui.COLOR_BUTTON, 1.0, 0.0, 0.0, 1.0)
            imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, 1.0, 0.0, 0.0, 1.0)
        clicked = imgui.button("Click me")
        if active:
            imgui.pop_style_color(2)
        imgui.pop_style_color(1)
        if read_only:
            return
        value.value = 1.0 if clicked else 0.0

class Int:
    def __init__(self, node, minmax=[float("-inf"), float("inf")]):
        self.node = node
        self.minmax = minmax
        self.clamper = clamper(minmax)

    def show(self, value, read_only):
        imgui.push_item_width(100)
        changed, v = imgui.input_int("", value.value)
        if changed and not read_only:
            value.value = int(self.clamper(v))

class Choice:
    def __init__(self, node, choices=[]):
        self.node = node
        self.choices = [ "(%d) %s" % (i, choice) for i, choice in enumerate(choices) ]

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
        if imgui.color_button("color %s" % id(self), r, g, b, a, flags, 50, 50):
            imgui.open_popup("picker %s" % id(self))
        if imgui.begin_popup("picker %s" % id(self)):
            changed, color = imgui.color_picker4("color", r, g, b, a, imgui.COLOR_EDIT_ALPHA_PREVIEW)
            if changed:
                if not read_only:
                    # careful here! update it safely (with numpy-assignment)
                    # but also set it properly so it is regarded as changed
                    v = value.value
                    v[:] = color
                    value.value = v
            imgui.end_popup()

def show_file_menu(base_path):
    try:
        entries = []
        for name in os.listdir(base_path):
            entries.append((not os.path.isdir(os.path.join(base_path, name)), name))

        for not_is_dir, name in sorted(entries):
            if not not_is_dir:
                if imgui.begin_menu(name):
                    selected_path = show_file_menu(os.path.join(base_path, name))
                    imgui.end_menu()
                    if selected_path is not None:
                        return os.path.join(base_path, selected_path)
            else:
                clicked, state = imgui.menu_item(name, None, False)
                if clicked:
                    return os.path.join(base_path, name)
    except:
        imgui.text("Error")

class AssetPath:
    def __init__(self, node, prefix=""):
        self.prefix = prefix

    def show(self, value, read_only):
        imgui.push_item_width(100)
        changed, v = imgui.input_text("", value.value, 255)
        imgui.push_item_width(100)
        if imgui.button("Select file"):
            imgui.open_popup("select_file")
        if imgui.begin_popup("select_file"):
            selected_path = show_file_menu(assets.ASSET_PATH + "/" + self.prefix)
            if selected_path is not None:
                value.value = selected_path
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
        imgui.set_next_window_size(1920 * 0.3, 1080 * 0.3 + 30, imgui.ONCE)
        imgui.set_next_window_position(*imgui.get_io().mouse_pos, imgui.ONCE, pivot_x=0.5, pivot_y=0.5)
        expanded, opened = imgui.begin("Texture of %s###%s%s" % (self.node.spec.name, id(self.node), id(self)), True, imgui.WINDOW_NO_SCROLLBAR)
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

