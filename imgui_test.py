#!/usr/bin/env python3

import sys
from vispy import app, gloo, keys
import imgui, vispy_imgui

canvas = app.Canvas(keys='interactive', vsync=False, autoswap=True)
timer = app.Timer(1.0 / 30.0, connect=canvas.update, start=True)
imgui_renderer = vispy_imgui.GlumpyGlfwRenderer(canvas.native, True)

closed = False

def t_mul(t1, scalar):
    return (t1[0]*scalar, t1[1]*scalar)

def t_add(t1, t2):
    return (t1[0]+t2[0], t1[1]+t2[1])

def t_sub(t1, t2):
    return (t1[0]-t2[0], t1[1]-t2[1])

def t_between(t1, t2, x):
    return t1[0] <= x[0] < t2[0] and t1[1] <= x[1] < t2[1]

COLOR_EDITOR_BACKGROUND = imgui.get_color_u32_rgba(0.1, 0.1, 0.1, 1.0)
COLOR_EDITOR_GRID = imgui.get_color_u32_rgba(0.3, 0.3, 0.3, 1.0)
COLOR_NODE_BACKGROUND = imgui.get_color_u32_rgba(0.0, 0.0, 0.0, 1.0)
COLOR_NODE_BORDER = imgui.get_color_u32_rgba(0.7, 0.7, 0.7, 1.0)
COLOR_NODE_BORDER_HOVERED = imgui.get_color_u32_rgba(1.0, 1.0, 1.0, 1.0)

class Node:
    id_counter = 0
    def __init__(self, editor, pos=(100, 100)):
        self.editor = editor
        self.window_id = Node.id_counter
        Node.id_counter += 1

        self.name = "TestNode"

        self.inputs = []
        self.outputs = [
            ("output", "float"),
        ]

        self.padding = 10, 10
        self.pos = pos
        self.size = 10, 10

        self.expanded = True
        self.dragging = False
        self.hovered = False

    @property
    def size_with_padding(self):
        return t_add(self.size, t_mul(self.padding, 2))

    def show(self, draw_list):
        io = imgui.get_io()

        imgui.push_id(self.window_id)
        old_cursor_pos = imgui.get_cursor_pos()

        if self.dragging:
            self.pos = t_add(self.pos, imgui.get_mouse_drag_delta())
            imgui.reset_mouse_drag_delta()

        upper_left = self.editor.local_to_screen(self.pos)
        lower_right = t_add(upper_left, self.size_with_padding)
        draw_list.add_rect_filled(upper_left, lower_right, COLOR_NODE_BACKGROUND, 5.0)

        # set_cursor_pos is already in window coordinates
        imgui.set_cursor_pos(t_add(self.pos, self.padding))
        imgui.begin_group()

        if imgui.button("[-]" if self.expanded else "[+]"):
            self.expanded = not self.expanded
        imgui.same_line()
        imgui.text("TestNode")
        imgui.same_line()
        if imgui.button("[x]"):
            imgui.open_popup("confirm_delete")
        if imgui.begin_popup("confirm_delete"):
            imgui.menu_item("Delete node?", None, False, False)
            imgui.menu_item("Nope")
            if imgui.menu_item("Yep yep yep")[0]:
                self.editor.remove_node(self)
            imgui.end_popup()

        if self.expanded:
            imgui.begin_group()
            imgui.text("Inputs")
            imgui.text("Hello!")
            imgui.dummy(50, 100)
            imgui.end_group()
            imgui.same_line()

            imgui.begin_group()
            imgui.text("Outputs")
            imgui.begin_group()
            for name, type in self.outputs:
                imgui.text("%s : %s" % (name, type))
            imgui.end_group()
            w = imgui.calculate_item_width()
            imgui.end_group()

            imgui.text("Output width: %d" % w)
        imgui.end_group()

        self.size = imgui.get_item_rect_size()
        mouse_pos = self.editor.screen_to_local(io.mouse_pos)
        self.hovered = imgui.is_window_hovered() and t_between(self.pos, t_add(self.pos, self.size_with_padding), mouse_pos)
        if self.hovered and imgui.is_mouse_clicked(0):
            self.dragging = True
        if imgui.is_mouse_released(0):
            self.dragging = False

        upper_left = self.editor.local_to_screen(self.pos)
        lower_right = t_add(upper_left, self.size_with_padding)
        color = COLOR_NODE_BORDER_HOVERED if self.hovered else COLOR_NODE_BORDER
        draw_list.add_rect(upper_left, lower_right, color, 5.0)

        imgui.pop_id()
        imgui.set_cursor_pos(old_cursor_pos)

class NodeEditor:
    def __init__(self):
        self.nodes = [Node(self, pos=(100, 100))]

        # window position in screen space
        self.pos = (0, 0)
        self.size = (1, 1)

    def local_to_screen(self, pos):
        return t_add(self.pos, pos)

    def screen_to_local(self, pos):
        return t_sub(pos, self.pos)

    def remove_node(self, node):
        self.nodes.remove(node)

    def show(self):
        io = imgui.get_io()
        w, h = io.display_size

        imgui.set_next_window_position(0, 0)
        imgui.set_next_window_size(w, h * 0.75)

        flags = imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_MOVE
        expanded, _ = imgui.begin("NodeEditor", False, flags)
        self.pos = imgui.get_window_position()
        self.size = imgui.get_window_size()
        if expanded:
            draw_list = imgui.get_window_draw_list()
            draw_list.add_rect_filled(self.pos, t_add(self.pos, self.size), COLOR_EDITOR_BACKGROUND)

            grid_size = 50
            for x in range(0, int(self.size[0]), grid_size):
                draw_list.add_line(t_add(self.pos, (x, 0)), t_add(self.pos, (x, self.size[1])), COLOR_EDITOR_GRID)
            for y in range(0, int(self.size[1]), grid_size):
                draw_list.add_line(t_add(self.pos, (0, y)), t_add(self.pos, (self.size[0], y)), COLOR_EDITOR_GRID)
            for node in self.nodes:
                node.show(draw_list)

            imgui.text("I'm expanded!")

            if imgui.is_mouse_clicked(1) and imgui.is_window_hovered() \
                    and not any(map(lambda n: n.hovered, self.nodes)):
                imgui.open_popup("context")
            if imgui.begin_popup("context"):
                if imgui.menu_item("TestNode")[0]:
                    pos = io.mouse_pos
                    self.nodes.append(Node(self, pos=pos))
                for name in ["FooNode", "BlahNode"]:
                    imgui.menu_item(name)
                imgui.separator()
                if imgui.begin_menu("More Nodes"):
                    imgui.menu_item("AnotherNode")
                    imgui.end_menu()
                imgui.end_popup()
        imgui.end()

editor = NodeEditor()

@canvas.connect
def on_draw(event):
    global closed

    gloo.set_clear_color((0.2, 0.4, 0.6, 1.0))
    # TODO why does gloo.clear not work?
    #gloo.clear(depth=True, color=True)
    gloo.gl.glClear(gloo.gl.GL_COLOR_BUFFER_BIT)

    imgui_renderer.process_inputs()
    imgui.new_frame()
    imgui.show_test_window()

    editor.show()

    if not closed:
        flags = imgui.WINDOW_NO_RESIZE | imgui.WINDOW_ALWAYS_AUTO_RESIZE
        flags = 0
        expanded, opened = imgui.begin("TestNode", True, flags)
        if expanded and False:
            w_pos = imgui.get_window_position()
            w_size = imgui.get_window_size()
            line_height = imgui.get_text_line_height()
            draw_list = imgui.get_window_draw_list()
            #draw_list.add_rect_filled(w_pos.x - 10, w_pos.y + 80, w_pos.x + 10, w_pos.y + 80 + 20, imgui.get_color_u32_rgba(1, 1, 0, 1))

            width_avail = imgui.get_content_region_available_width()
            imgui.text("%d pixels wide" % width_avail)
            imgui.columns(2, "mixed")
            width_avail = imgui.get_content_region_available_width()
            imgui.text("%d pixels wide" % width_avail)
            imgui.same_line()
            width_avail = imgui.get_content_region_available_width()
            imgui.text("only %d more for me!" % width_avail)
            imgui.text("Inputs")
            imgui.next_column()
            imgui.text("Outputs")
            imgui.text("Test!")
            imgui.text("My window is at %d:%d" % (w_pos.x, w_pos.y))
            pos = imgui.get_cursor_screen_pos()
            imgui.text("I start at %d:%d" % (pos.x, pos.y))
            pos = imgui.get_cursor_screen_pos()
            imgui.dummy(line_height, line_height)
            #draw_list.add_rect_filled(pos.x, pos.y, pos.x + line_height, pos.y + line_height, imgui.get_color_u32_rgba(1, 1, 0, 1))
        imgui.end()
        if not opened:
            print("was closed!")
            closed = True

    #imgui.set_next_window_position(10, 10, condition=imgui.ALWAYS, pivot_x=0, pivot_y=0)
    #imgui.set_next_window_size(0.0, 0.0)
    #flags = imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_RESIZE + imgui.WINDOW_NO_MOVE + imgui.WINDOW_NO_COLLAPSE

    #imgui.begin("Stats", None, flags)
    #imgui.text("FPS: %.2f" % app.clock.get_fps())
    #imgui.text("Current BPM: %.2f" % current_bpm.value)
    #imgui.text("Beat running: %s" % {True : "Yes", False : "Nope"}[is_beat_running])
    #imgui.end()

    imgui.render()
    draw = imgui.get_draw_data()
    imgui_renderer.render(draw)

@canvas.connect
def on_key_press(event):
    if event.key == "q":
        sys.exit(0)

if __name__ == "__main__":
    canvas.show()
    app.run()
