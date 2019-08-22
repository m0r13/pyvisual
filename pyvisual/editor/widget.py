# TODO naming
import os
import fnmatch
import pyvisual.node as node_meta
import pyvisual.node.dtype as dtypes
from pyvisual.node.value import ConnectedValue
from pyvisual import assets, util
from PIL import Image

import clipboard
import numpy as np
import time
import contextlib
import imgui

def clamper(minmax):
    return lambda x: max(minmax[0], (min(minmax[1], x)))

@contextlib.contextmanager
def read_only_widget(read_only):
    # TODO also "gray-out" widget
    if read_only:
        imgui.push_item_flag(imgui.ITEM_DISABLED, True)

    yield

    if read_only:
        imgui.pop_item_flag()

WIDGET_WIDTH = 80

DEFAULT_UNIT_DRAG_FACTOR = 1.0
UNIT_DRAG_FACTORS = {
    "px" : 25.0,
    "deg" : 5.0,
}

def create_widget(dtype, dtype_args, node=None):
    widget_types = {
        dtypes.bool: Bool,
        dtypes.event: Button,
        dtypes.int: Int,
        dtypes.float: Float,
        dtypes.vec2: Vec2,
        dtypes.color: Color,
        dtypes.str: String,
        dtypes.tex2d: Texture,
    }

    # TODO maybe just pass dtype_args to widget?
    kwargs = {}
    if dtype in (dtypes.float, dtypes.vec2):
        kwargs["drag_factor"] = UNIT_DRAG_FACTORS.get(dtype_args.get("unit", ""), DEFAULT_UNIT_DRAG_FACTOR)
    if "range" in dtype_args:
        kwargs["minmax"] = dtype_args["range"]

    if dtype == dtypes.int and "choices" in dtype_args:
        return Choice(node, choices=dtype_args["choices"])
    if dtype == dtypes.str and dtype_args.get("variant") == "text":
        return Text(node)
    if dtype == dtypes.assetpath:
        return AssetPath(node, prefix=dtype_args.get("prefix", ""))
    if dtype in widget_types:
        return widget_types[dtype](node, **kwargs)
    return None

class Widget:
    def __init__(self, ignore_read_only=False):
        self._ignore_read_only = ignore_read_only

        self.width = WIDGET_WIDTH

    def _show(self):
        pass

    def show(self, value, read_only):
        # TODO also "gray-out" widget
        if read_only and not self._ignore_read_only:
            imgui.push_item_flag(imgui.ITEM_DISABLED, True)

        self._show(value, read_only)

        if read_only and not self._ignore_read_only:
            imgui.pop_item_flag()

class Bool(Widget):
    def __init__(self, node):
        super().__init__()

    def _show(self, value, read_only):
        clicked, state = imgui.checkbox("", value.value)
        if clicked and not read_only:
            value.value = state

class Button(Widget):
    ACTIVE_TIME = 0.1
    def __init__(self, node):
        super().__init__(ignore_read_only=True)

        # when the event was last triggered
        self._last_active = 0

    def _show(self, value, read_only):
        active = value.value or time.time() - self._last_active < Button.ACTIVE_TIME
        if value.value:
            self._last_active = time.time()
        imgui.push_style_color(imgui.COLOR_BUTTON_ACTIVE, 1.0, 0.0, 0.0, 1.0)
        if active:
            imgui.push_style_color(imgui.COLOR_BUTTON, 1.0, 0.0, 0.0, 1.0)
            imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, 1.0, 0.0, 0.0, 1.0)
        imgui.push_item_width(self.width)
        clicked = imgui.button("Click me")
        if active:
            imgui.pop_style_color(2)
        imgui.pop_style_color(1)

        # TODO this might be a problem
        # events are reset by this widget!

        # events are a special case!!
        # this widget gets InputValueHolder value even when an input is connected
        #   (to make sure that event trigger is displayed on the button)
        # when button is pressed even though a value is connected:
        # -> set force flag on manual value, don't forget to reset it
        value_to_set = value
        if isinstance(value, ConnectedValue):
            value_to_set = value.manual_value

        # when the button is clicked we use the force value option of the manual value
        if clicked:
            value_to_set.force_value = True
        # and reset it again in the next frame
        elif value_to_set.force_value:
            value_to_set.force_value = False

import sys

class Int(Widget):
    def __init__(self, node, minmax=[float("-inf"), float("inf")]):
        super().__init__()

        self.node = node
        self.minmax = minmax
        self.clamper = clamper(minmax)

    def _show(self, value, read_only):
        imgui.push_item_width(self.width)
        vv = value.value
        if vv == float("inf"):
            vv = 2147483647
        elif vv == float("-inf"):
            vv = -2147483648
        changed, v = imgui.input_int("", vv)
        if changed and not read_only:
            value.value = int(self.clamper(v))

class Choice(Widget):
    def __init__(self, node, choices=[]):
        super().__init__()

        self.node = node
        #self.choices = [ "(%d) %s" % (i, choice) for i, choice in enumerate(choices) ]
        self.choices = [ choice for i, choice in enumerate(choices) ]

    def _show(self, value, read_only):
        imgui.push_item_width(self.width)
        changed, v = imgui.combo("", value.value, self.choices)
        if changed and not read_only:
            value.value = v
        if imgui.is_item_hovered() and imgui.is_mouse_clicked(2):
            imgui.open_popup("choice_context")
        if imgui.begin_popup("choice_context"):
            if imgui.menu_item("copy choices")[0]:
                clipboard.copy("\n".join(self.choices))
            imgui.end_popup()

class Float(Widget):
    def __init__(self, node, drag_factor=1.0, minmax=[float("-inf"), float("inf")]):
        super().__init__()

        self.node = node
        self.drag_factor = 0.01 * drag_factor
        self.minmax = minmax
        self.clamper = clamper(minmax)

        self.width *= 0.75

    def _show(self, value, read_only):
        imgui.push_item_width(self.width)
        vv = value.value
        # TODO workaround for port widgets being updated only every N frames
        # it can happen that a float widget is replaced by a texture widget (ModuleInput node for example)
        # and the float widget receives the texture value (None) for a few frames
        # this prevents imgui from failing because None was passed
        if vv is None:
            vv = 0.0
        changed, v = imgui.drag_float("", vv,
                change_speed=self.drag_factor, min_value=self.minmax[0] or float("-inf"), max_value=self.minmax[1] or float("inf"), format="%0.4f")
        if changed and not read_only:
            value.value = self.clamper(v)

class Vec2(Widget):
    def __init__(self, node, drag_factor=1.0):
        super().__init__()

        self.node = node
        self.drag_factor = 0.01 * drag_factor

        self.width *= 0.75

    def _show(self, value, read_only):
        imgui.push_item_width(self.width)
        imgui.push_id("v0")
        changed0, v0 = imgui.drag_float("", value.value[0], change_speed=self.drag_factor, format="%0.4f")
        imgui.pop_id()

        imgui.push_item_width(self.width)
        imgui.push_id("v1")
        changed1, v1 = imgui.drag_float("", value.value[1], change_speed=self.drag_factor, format="%0.4f")
        imgui.pop_id()

        if (changed0 or changed1) and not read_only:
            value.value = np.array([v0, v1])

class Color(Widget):
    def __init__(self, node):
        super().__init__()

    def show(self, value, read_only):
        # don't show it as read-only for now
        # as the color picker dialog might be nice for inspecting the color
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

def imgui_pick_file(name, base_path, wildcard="*"):
    if imgui.begin_popup(name):
        path = imgui_pick_file_menu(base_path, wildcard)
        if path is not None:
            imgui.close_current_popup()
            imgui.end_popup()
            return path
        imgui.end_popup()

WILDCARDS = ["*.jpg", "*.png"]
def imgui_pick_file_menu(base_path, wildcard="*"):
    MAX_FILE_DISPLAY_LENGTH = 60

    try:
        entries = []
        for name in os.listdir(base_path):
            entries.append((not os.path.isdir(os.path.join(base_path, name)), name))

        imgui.text("New:")
        imgui.same_line()
        imgui.push_item_width(-1)
        changed, value = imgui.input_text("", "", 255, imgui.INPUT_TEXT_ENTER_RETURNS_TRUE)
        if changed:
            return os.path.join(base_path, value)
        imgui.separator()
        for w in WILDCARDS:
            if imgui.button(w):
                return os.path.join(base_path, w)
            imgui.same_line()
        imgui.dummy(0, 0)
        imgui.separator()

        if len(entries) == 0:
            imgui.dummy(200, 0)

        for not_is_dir, name in sorted(entries):
            display_name = name
            if len(display_name) > MAX_FILE_DISPLAY_LENGTH:
                display_name = display_name[:MAX_FILE_DISPLAY_LENGTH//2] + "..." + display_name[-MAX_FILE_DISPLAY_LENGTH//2:]

            if not not_is_dir:
                if imgui.begin_menu(display_name):
                    selected_path = imgui_pick_file_menu(os.path.join(base_path, name), wildcard)
                    imgui.end_menu()
                    if selected_path is not None:
                        return os.path.join(base_path, selected_path)
            else:
                if not fnmatch.fnmatch(name, wildcard):
                    continue
                clicked, state = imgui.menu_item(display_name, None, False)
                if clicked:
                    return os.path.join(base_path, name)

        imgui.separator()
        imgui.text("Pick: %s" % wildcard)
    except:
        imgui.text("Unable to open dir")

class String(Widget):
    def __init__(self, node):
        super().__init__()

    def _show(self, value, read_only):
        imgui.push_item_width(self.width)
        changed, v = imgui.input_text("", value.value, 255, imgui.INPUT_TEXT_ENTER_RETURNS_TRUE)
        if imgui.is_item_hovered() and not imgui.is_item_active():
            imgui.set_tooltip(value.value)
        if changed:
            value.value = v

class Text(Widget):
    def __init__(self, node):
        super().__init__()

    def _show(self, value, read_only):
        changed, v = imgui.input_text_multiline("", value.value, 2048, self.width, 200)
        if changed:
            value.value = v

class AssetPath(Widget):
    def __init__(self, node, prefix=""):
        super().__init__()

        self.prefix = prefix

    def _show(self, value, read_only):
        imgui.push_item_width(self.width)
        changed, v = imgui.input_text("", value.value, 255, imgui.INPUT_TEXT_ENTER_RETURNS_TRUE)
        if imgui.is_item_hovered() and not imgui.is_item_active():
            imgui.set_tooltip(value.value)
        if changed:
            value.value = v
            return
        imgui.push_item_width(self.width)
        if imgui.button("Select file"):
            imgui.open_popup("select_file")

        path = imgui_pick_file("select_file", assets.ASSET_PATH + "/" + self.prefix)
        if path is not None:
            value.value = os.path.relpath(path, assets.ASSET_PATH)

class Texture(Widget):
    def __init__(self, node):
        super().__init__()

        self.node = node
        self.show_texture = False

        self.texture_aspect = None

        def window_size_callback(size, self=self):
            aspect = self.texture_aspect
            if aspect is None:
                return size

            w, h = size
            w1, h1 = aspect * h, h
            w2, h2 = w, w / aspect
            if w1 < w2:
                return w1, h1 + 30
            else:
                return w2, h2 + 30
        self.window_size_callback = window_size_callback

    def show(self, value, read_only):
        clicked, self.show_texture = imgui.checkbox("Show", self.show_texture)
        if not self.show_texture:
            return

        texture = value.value
        if texture is None:
            self.texture_aspect = None
        else:
            h, w, _ = texture.shape
            self.texture_aspect = w / h

        cursor_pos = imgui.get_cursor_screen_pos()
        imgui.set_next_window_size(500, 500, imgui.ONCE)
        imgui.set_next_window_size_constraints((0.0, 0.0), (float("inf"), float("inf")), self.window_size_callback)
        imgui.set_next_window_position(*imgui.get_io().mouse_pos, imgui.ONCE, pivot_x=0.5, pivot_y=0.5)
        expanded, opened = imgui.begin("Texture of %s###%s%s" % (self.node.spec.name, id(self.node), id(self)), True, imgui.WINDOW_NO_SCROLLBAR)
        if not opened:
            self.show_texture = False
        if expanded:
            if texture is None:
                imgui.text("No texture associated")
            else:
                # [::-1] reverses list
                texture_size = texture.shape[:2][::-1]
                texture_aspect = texture_size[0] / texture_size[1]
                window_size = imgui.get_content_region_available()
                imgui.image(texture._handle, window_size[0], window_size[0] / texture_aspect)
                if imgui.is_item_hovered() and imgui.is_mouse_clicked(1):
                    # little hack to have first context menu entry under cursor
                    io = imgui.get_io()
                    pos = io.mouse_pos
                    io.mouse_pos = pos[0] - 20, pos[1] - 20
                    imgui.open_popup("context")
                    io.mouse_pos = pos
                if imgui.begin_popup("context"):
                    if imgui.menu_item("save")[0]:
                        util.image.save_screenshot(texture.get())
                    imgui.menu_item("texture handle: %s" % texture._handle, None, False, False)
                    imgui.menu_item("texture dtype: %s" % str(texture.dtype), None, False, False)
                    imgui.menu_item("texture shape: %s" % str(texture.shape), None, False, False)
                    imgui.end_popup()
            imgui.end()

