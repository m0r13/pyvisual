import glumpy.ext.glfw as glfw
import imgui

from imgui.integrations.opengl import ProgrammablePipelineRenderer

# HACK
class FixedProgrammablePipelineRenderer(ProgrammablePipelineRenderer):
    VERTEX_SHADER_SRC = ProgrammablePipelineRenderer.VERTEX_SHADER_SRC.replace("#version 330", "#version 130")
    FRAGMENT_SHADER_SRC = ProgrammablePipelineRenderer.FRAGMENT_SHADER_SRC.replace("#version 330", "#version 130")

class GlumpyGlfwRenderer(FixedProgrammablePipelineRenderer):
    def __init__(self, window, attach_callbacks=True):
        super(GlumpyGlfwRenderer, self).__init__()
        self.window = window
        self.handle = window._native_window

        if attach_callbacks:
            glfw.glfwSetKeyCallback(self.handle, self.keyboard_callback)
            glfw.glfwSetCursorPosCallback(self.handle, self.mouse_callback)
            glfw.glfwSetWindowSizeCallback(self.handle, self.resize_callback)
            glfw.glfwSetCharCallback(self.handle, self.char_callback)
            glfw.glfwSetScrollCallback(self.handle, self.scroll_callback)

        self.io.display_size = glfw.glfwGetFramebufferSize(self.handle)

        self._map_keys()
        self._gui_time = None

    def _map_keys(self):
        key_map = self.io.key_map

        key_map[imgui.KEY_TAB] = glfw.GLFW_KEY_TAB
        key_map[imgui.KEY_LEFT_ARROW] = glfw.GLFW_KEY_LEFT
        key_map[imgui.KEY_RIGHT_ARROW] = glfw.GLFW_KEY_RIGHT
        key_map[imgui.KEY_UP_ARROW] = glfw.GLFW_KEY_UP
        key_map[imgui.KEY_DOWN_ARROW] = glfw.GLFW_KEY_DOWN
        key_map[imgui.KEY_PAGE_UP] = glfw.GLFW_KEY_PAGE_UP
        key_map[imgui.KEY_PAGE_DOWN] = glfw.GLFW_KEY_PAGE_DOWN
        key_map[imgui.KEY_HOME] = glfw.GLFW_KEY_HOME
        key_map[imgui.KEY_END] = glfw.GLFW_KEY_END
        key_map[imgui.KEY_DELETE] = glfw.GLFW_KEY_DELETE
        key_map[imgui.KEY_BACKSPACE] = glfw.GLFW_KEY_BACKSPACE
        key_map[imgui.KEY_SPACE] = glfw.GLFW_KEY_SPACE
        key_map[imgui.KEY_ENTER] = glfw.GLFW_KEY_ENTER
        key_map[imgui.KEY_ESCAPE] = glfw.GLFW_KEY_ESCAPE
        key_map[imgui.KEY_A] = glfw.GLFW_KEY_A
        key_map[imgui.KEY_C] = glfw.GLFW_KEY_C
        key_map[imgui.KEY_V] = glfw.GLFW_KEY_V
        key_map[imgui.KEY_X] = glfw.GLFW_KEY_X
        key_map[imgui.KEY_Y] = glfw.GLFW_KEY_Y
        key_map[imgui.KEY_Z] = glfw.GLFW_KEY_Z

    def keyboard_callback(self, window, key, scancode, action, mods):
        # perf: local for faster access
        io = self.io

        if action == glfw.GLFW_PRESS:
            io.keys_down[key] = True
        elif action == glfw.GLFW_RELEASE:
            io.keys_down[key] = False

        io.key_ctrl = (
            io.keys_down[glfw.GLFW_KEY_LEFT_CONTROL] or
            io.keys_down[glfw.GLFW_KEY_RIGHT_CONTROL]
        )

        io.key_alt = (
            io.keys_down[glfw.GLFW_KEY_LEFT_ALT] or
            io.keys_down[glfw.GLFW_KEY_RIGHT_ALT]
        )

        io.key_shift = (
            io.keys_down[glfw.GLFW_KEY_LEFT_SHIFT] or
            io.keys_down[glfw.GLFW_KEY_RIGHT_SHIFT]
        )

        io.key_super = (
            io.keys_down[glfw.GLFW_KEY_LEFT_SUPER] or
            io.keys_down[glfw.GLFW_KEY_RIGHT_SUPER]
        )

        if not io.want_capture_keyboard and not io.want_text_input:
            self.window.on_keyboard(window, key, scancode, action, mods)

    def char_callback(self, window, char):
        io = imgui.get_io()

        if 0 < char < 0x10000:
            io.add_input_character(char)

        if not io.want_capture_keyboard and not io.want_text_input:
            self.window.on_keyboard_char(window, char)

    def resize_callback(self, window, width, height):
        self.io.display_size = width, height

        # no callback for this in glumpy glfw backend

    def mouse_callback(self, *args, **kwargs):
        pass
        #self.window.on_mouse_motion(*args, **kwargs)

    def scroll_callback(self, window, x_offset, y_offset):
        self.io.mouse_wheel = y_offset

        #self.window.on_scroll(window, x_offset, y_offset)

    def process_inputs(self):
        # todo: consider moving to init
        io = imgui.get_io()

        w, h = glfw.glfwGetWindowSize(self.handle)
        dw, dh = glfw.glfwGetFramebufferSize(self.handle)

        io.display_size = w, h
        io.display_fb_scale = float(dw)/w, float(dh)/h

        io.delta_time = 1.0/60

        if glfw.glfwGetWindowAttrib(self.handle, glfw.GLFW_FOCUSED):
            io.mouse_pos = glfw.glfwGetCursorPos(self.handle)
        else:
            io.mouse_pos = -1, -1

        io.mouse_down[0] = glfw.glfwGetMouseButton(self.handle, 0)
        io.mouse_down[1] = glfw.glfwGetMouseButton(self.handle, 1)
        io.mouse_down[2] = glfw.glfwGetMouseButton(self.handle, 2)

        current_time = glfw.glfwGetTime()

        if self._gui_time:
            self.io.delta_time = current_time - self._gui_time
        else:
            self.io.delta_time = 1. / 60.

        self._gui_time = current_time
