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

def t_circle_contains(center, radius, point):
    a = t_add(center, (-radius, -radius))
    b = t_add(center, (radius, radius))
    if not t_between(a, b, point):
        return False
    return True

COLOR_EDITOR_BACKGROUND = imgui.get_color_u32_rgba(0.1, 0.1, 0.1, 1.0)
COLOR_EDITOR_GRID = imgui.get_color_u32_rgba(0.3, 0.3, 0.3, 1.0)
COLOR_NODE_BACKGROUND = imgui.get_color_u32_rgba(0.0, 0.0, 0.0, 1.0)
COLOR_NODE_BORDER = imgui.get_color_u32_rgba(0.7, 0.7, 0.7, 1.0)
COLOR_NODE_BORDER_HOVERED = COLOR_NODE_BORDER

COLOR_PORT_HIGHLIGHT_POSITIVE = imgui.get_color_u32_rgba(0.0, 0.5, 0.0, 1.0)
COLOR_PORT_HIGHLIGHT_POSITIVE_ACTIVE = imgui.get_color_u32_rgba(0.5, 0.5, 0.0, 1.0)
COLOR_PORT_HIGHLIGHT_NEUTRAL = imgui.get_color_u32_rgba(0.0, 0.0, 0.0, 0.0)
COLOR_PORT_HIGHLIGHT_NEGATIVE = imgui.get_color_u32_rgba(0.5, 0.5, 0.5, 0.5)
COLOR_PORT_BULLET = imgui.get_color_u32_rgba(1.0, 0.0, 0.0, 1.0)
COLOR_PORT_BULLET_HOVERED = imgui.get_color_u32_rgba(1.0, 1.0, 0.0, 1.0)
COLOR_PORT_BULLET_DROPPABLE = imgui.get_color_u32_rgba(0.0, 1.0, 0.0, 1.0)
COLOR_PORT_BULLET_DISABLED = COLOR_NODE_BORDER

CHANNEL_BACKGROUND = 0
CHANNEL_DEFAULT = 1
CHANNEL_NODE_BACKGROUND = 2
CHANNEL_NODE = 3
CHANNEL_CONNECTION = 4
CHANNEL_PORT = 5

CHANNEL_COUNT = 6

class draw_on_channel:
    def __init__(self, draw_list, channel):
        self.draw_list = draw_list
        self.old_channel = None
        self.new_channel = channel

    def __enter__(self):
        self.old_channel = self.draw_list.channels_current
        self.draw_list.channels_set_current(self.new_channel)
    def __exit__(self, *args):
        assert self.old_channel is not None
        self.draw_list.channels_set_current(self.old_channel)
        return False

PORT_TYPE_INPUT = 0
PORT_TYPE_OUTPUT = 1
def opposite_port_type(port_type):
    assert 0 <= port_type <= 1
    return 0 if port_type == 1 else 1

class Connection:
    def __init__(self, editor, input_node, input_index, output_node, output_index):
        self.editor = editor
        self.input_node = input_node
        self.input_index = input_index
        self.output_node = output_node
        self.output_index = output_index
        self.connect()

    def connect(self):
        self.input_node.attach_connection(PORT_TYPE_OUTPUT, self.input_index, self)
        self.output_node.attach_connection(PORT_TYPE_INPUT, self.output_index, self)

    def disconnect(self):
        self.input_node.detach_connection(PORT_TYPE_OUTPUT, self.input_index, self)
        self.output_node.detach_connection(PORT_TYPE_INPUT, self.output_index, self)

    def show(self, draw_list):
        # is connected when both sides are on a node
        connected = not isinstance(self.input_node, MouseDummyNode) \
                and not isinstance(self.output_node, MouseDummyNode)
        dragging_connection = self.editor.is_dragging_connection()

        color = COLOR_PORT_BULLET
        if dragging_connection and connected:
            # show connections while other connection is dragged as inactive
            color = COLOR_PORT_BULLET_DISABLED
        elif dragging_connection and not connected:
            # show connection that is being dragged as active
            color = COLOR_PORT_BULLET_HOVERED

        p1 = self.input_node.get_port_position(PORT_TYPE_OUTPUT, self.input_index)
        p2 = self.output_node.get_port_position(PORT_TYPE_INPUT, self.output_index)
        with draw_on_channel(draw_list, CHANNEL_CONNECTION):
            draw_list.add_line(p1, p2, color, 2.0)

    @staticmethod
    def create(editor, node, port_type, port_index):
        if port_type == PORT_TYPE_INPUT:
            return Connection(editor, output_node=node, output_index=port_index,
                    input_node=MouseDummyNode(), input_index=-1)
        else:
            return Connection(editor, input_node=node, input_index=port_index,
                    output_node=MouseDummyNode(), output_index=-1)

class MouseDummyNode:
    def attach_connection(self, *args):
        pass
    def detach_connection(self, *args):
        pass

    def get_port_position(self, port_type, port_index):
        return imgui.get_io().mouse_pos

class Node:
    id_counter = 0
    def __init__(self, editor, pos=(100, 100)):
        self.editor = editor
        self.window_id = Node.id_counter
        Node.id_counter += 1

        self.name = "TestNode"

        inputs = [
            ("input", "int"),
            ("input2", "float"),
        ]
        outputs = [
            ("output", "float"),
            ("output2", "int"),
        ]
        self.ports = (inputs, outputs)
        self.port_positions = ([None]*len(inputs), [None]*len(outputs))
        self.connections = ([[] for _ in inputs], [[] for _ in outputs])

        self.padding = 12, 12
        # local position (without editor window pos or offset)
        self.pos = pos
        self.size = 10, 10

        self.expanded = True
        self.dragging = False
        self.hovered = False

    @property
    def size_with_padding(self):
        return t_add(self.size, t_mul(self.padding, 2))

    def attach_connection(self, port_type, port_index, connection):
        self.connections[port_type][port_index].append(connection)

    def detach_connection(self, port_type, port_index, connection):
        self.connections[port_type][port_index].remove(connection)

    def get_port_position(self, port_type, port_index):
        positions = self.port_positions[port_type]
        if not self.expanded or port_index >= len(positions) or positions[port_index] is None:
            x = self.pos[0] if port_type == PORT_TYPE_INPUT else self.pos[0]+self.size[0]+self.padding[0]*2
            y = self.pos[1] + (self.size[1] + self.padding[1] * 2) / 2
            return self.editor.local_to_screen((x, y))
        return positions[port_index]

    def show_ports(self, draw_list, ports, port_type):
        io = imgui.get_io()

        channel_stack = draw_on_channel(draw_list, CHANNEL_NODE)
        channel_stack.__enter__()

        imgui.push_id(int(port_type))
        imgui.begin_group()
        for port_index, (name, type) in enumerate(ports):
            # ui
            imgui.push_id(port_index)
            imgui.begin_group()
            # port_start is in screen coordinates now
            port_start = imgui.get_cursor_screen_pos()
            imgui.text("%s : %s" % (name, type))

            # position calculation
            size = imgui.get_item_rect_size()
            x = self.pos[0]
            if port_type == PORT_TYPE_OUTPUT:
                x += self.size[0] + self.padding[0]*2
            y = self.editor.screen_to_local(port_start)[1] + size[1] / 2
            radius = 6.0
            thickness = 2.0
            center = self.editor.local_to_screen((x, y))
            self.port_positions[port_type][port_index] = center

            imgui.push_item_width(100)
            imgui.input_float("", 0.0)
            imgui.end_group()

            # screen coordinates, like port_start
            port_end = imgui.get_item_rect_max()

            # port state
            dragging_connection = self.editor.is_dragging_connection()
            droppable = False
            if dragging_connection:
                droppable = self.editor.is_connection_droppable(self, port_type, port_index)
            connection_source = self.editor.is_dragging_connection_source(self, port_type, port_index)
            connections = self.connections[port_type][port_index]
            if port_type == PORT_TYPE_INPUT:
                assert len(connections) in (0, 1)

            hovered_bullet = t_circle_contains(center, radius, io.mouse_pos)
            hovered_port = t_between(port_start, port_end, io.mouse_pos)
            hovered = hovered_bullet or hovered_port

            # decide port bullet color
            bullet_color = COLOR_PORT_BULLET
            if dragging_connection and connection_source:
                # connection source is drawn as hovered
                bullet_color = COLOR_PORT_BULLET_HOVERED
            elif dragging_connection and not droppable:
                # any port where it's not droppable disabled
                bullet_color = COLOR_PORT_BULLET_DISABLED
            elif hovered_bullet or (dragging_connection and hovered_port):
                bullet_color = COLOR_PORT_BULLET_HOVERED
            elif dragging_connection and droppable:
                bullet_color = COLOR_PORT_BULLET_DROPPABLE

            # decide port highlight color
            highlight_channel = CHANNEL_NODE_BACKGROUND
            highlight_color = COLOR_PORT_HIGHLIGHT_NEUTRAL
            if dragging_connection and not connection_source:
                if not droppable:
                    highlight_channel = CHANNEL_NODE
                    highlight_color = COLOR_PORT_HIGHLIGHT_NEGATIVE
                else:
                    highlight_channel = CHANNEL_NODE_BACKGROUND
                    highlight_color = COLOR_PORT_HIGHLIGHT_POSITIVE

            # decide for action on port / port bullet
            deleteable = port_type == PORT_TYPE_INPUT and len(connections) > 0
            if hovered_bullet and deleteable and not dragging_connection:
                imgui.set_tooltip("Delete connection")
                if imgui.is_mouse_released(0):
                    self.editor.remove_connection(connections[0])
            elif hovered and dragging_connection and droppable:
                highlight_channel = CHANNEL_NODE_BACKGROUND
                highlight_color = COLOR_PORT_HIGHLIGHT_POSITIVE_ACTIVE
                imgui.set_tooltip("Drop connection")
                if imgui.is_mouse_released(0):
                    self.editor.drop_connection(self, port_type, port_index)
            elif not dragging_connection and hovered_bullet:
                imgui.set_tooltip("Create connection")
                if imgui.is_mouse_clicked(0):
                    self.editor.drag_connection(self, port_type, port_index)

            # port bullet drawing
            with draw_on_channel(draw_list, CHANNEL_PORT):
                if len(connections) > 0:
                    draw_list.add_circle_filled(center, radius, bullet_color)
                else:
                    draw_list.add_circle(center, radius, bullet_color, 12, thickness)

            # port highlight drawing
            with draw_on_channel(draw_list, highlight_channel):
                draw_list.add_rect_filled(port_start, port_end, highlight_color)

            imgui.pop_id()
        imgui.end_group()
        imgui.pop_id()

        channel_stack.__exit__()

    def show(self, draw_list):
        io = imgui.get_io()
        
        channel_stack = draw_on_channel(draw_list, CHANNEL_NODE)
        channel_stack.__enter__()

        imgui.push_id(self.window_id)
        old_cursor_pos = imgui.get_cursor_pos()

        if self.dragging:
            self.pos = t_add(self.pos, imgui.get_mouse_drag_delta())
            imgui.reset_mouse_drag_delta()

        upper_left = self.editor.local_to_screen(self.pos)
        lower_right = t_add(upper_left, self.size_with_padding)
        with draw_on_channel(draw_list, CHANNEL_NODE_BACKGROUND):
            draw_list.add_rect_filled(upper_left, lower_right, COLOR_NODE_BACKGROUND, 5.0)

        # set_cursor_pos is in window coordinates
        imgui.set_cursor_pos(self.editor.local_to_window(t_add(self.pos, self.padding)))
        imgui.begin_group()

        if imgui.button("[-]" if self.expanded else "[+]"):
            self.expanded = not self.expanded
        imgui.same_line()
        imgui.text("TestNode")
        imgui.same_line()
        if imgui.button("[x]"):
            self.editor.remove_node(self)

        if self.expanded:
            imgui.begin_group()
            self.show_ports(draw_list, self.ports[PORT_TYPE_INPUT], PORT_TYPE_INPUT)
            imgui.end_group()
            imgui.same_line()

            imgui.begin_group()
            self.show_ports(draw_list, self.ports[PORT_TYPE_OUTPUT], PORT_TYPE_OUTPUT)
            imgui.end_group()

        imgui.end_group()

        self.size = imgui.get_item_rect_size()
        mouse_pos = self.editor.screen_to_local(io.mouse_pos)
        self.hovered = imgui.is_window_hovered() and t_between(self.pos, t_add(self.pos, self.size_with_padding), mouse_pos)
        if self.hovered and imgui.is_mouse_clicked(0) and not self.editor.is_dragging_connection():
            self.dragging = True
        if imgui.is_mouse_released(0):
            self.dragging = False

        upper_left = self.editor.local_to_screen(self.pos)
        lower_right = t_add(upper_left, self.size_with_padding)
        color = COLOR_NODE_BORDER_HOVERED if self.hovered else COLOR_NODE_BORDER
        with draw_on_channel(draw_list, CHANNEL_NODE_BACKGROUND):
            draw_list.add_rect(upper_left, lower_right, color, 5.0)

        imgui.pop_id()
        imgui.set_cursor_pos(old_cursor_pos)

        channel_stack.__exit__()

class NodeEditor:
    def __init__(self):
        node1 = Node(self, pos=(50, 50))
        node2 = Node(self, pos=(500, 200))
        connection = Connection(self, output_node=node2, output_index=0, input_node=node1, input_index=0)
        self.nodes = [node1, node2]
        self.connections = [connection]

        # window position in screen space
        self.pos = (0, 0)
        self.size = (1, 1)

        # offset for moving position around
        # offset (100, 100) means that at window (0, 0) is local position (100, 100)
        self.offset = (0, 0)

        # state
        self.dragging_connection = None
        self.dragging_target_port_type = None

        self.dragging_position = False

    def local_to_window(self, pos):
        return t_sub(pos, self.offset)

    def local_to_screen(self, pos):
        return t_sub(t_add(self.pos, pos), self.offset)

    def screen_to_local(self, pos):
        return t_add(t_sub(pos, self.pos), self.offset)

    def remove_node(self, node):
        for port_type in (PORT_TYPE_INPUT, PORT_TYPE_OUTPUT):
            for connections in node.connections[port_type]:
                for connection in connections:
                    self.remove_connection(connection)
        self.nodes.remove(node)

    def remove_connection(self, connection):
        connection.disconnect()
        self.connections.remove(connection)

    def drag_connection(self, node, port_type, port_index):
        assert self.dragging_connection is None
        self.dragging_connection = Connection.create(self, node, port_type, port_index)
        self.dragging_target_port_type = opposite_port_type(port_type)
        self.connections.append(self.dragging_connection)

    def is_dragging_connection(self):
        return self.dragging_connection is not None

    def is_dragging_connection_source(self, node, port_type, port_index):
        if not self.is_dragging_connection():
            return False
        if port_type == PORT_TYPE_INPUT:
            return self.dragging_connection.output_node == node \
                    and self.dragging_connection.output_index == port_index
        else:
            return self.dragging_connection.input_node == node \
                    and self.dragging_connection.input_index == port_index

    def is_connection_droppable(self, node, port_type, port_index):
        assert self.is_dragging_connection()
        # constraint: connect only input with output and vice versa
        if port_type != self.dragging_target_port_type:
            return False
        # TODO prevent this manual hackish check?
        # constraint: only one connection per input
        if port_type == PORT_TYPE_INPUT:
            return len(node.connections[PORT_TYPE_INPUT][port_index]) == 0
        return True

    def drop_connection(self, node, port_type, port_index):
        assert self.is_dragging_connection()
        assert self.is_connection_droppable(node, port_type, port_index)

        self.dragging_connection.disconnect()
        if port_type == PORT_TYPE_INPUT:
            self.dragging_connection.output_node = node
            self.dragging_connection.output_index = port_index
        else:
            self.dragging_connection.input_node = node
            self.dragging_connection.input_index = port_index
        self.dragging_connection.connect()
        self.dragging_connection = None

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
            draw_list.channels_split(CHANNEL_COUNT)
            draw_list.channels_set_current(CHANNEL_DEFAULT)

            with draw_on_channel(draw_list, CHANNEL_BACKGROUND):
                draw_list.add_rect_filled(self.pos, t_add(self.pos, self.size), COLOR_EDITOR_BACKGROUND)
                # how does the grid work?
                #   -> find local coords where we see first grid pos
                #   -> build grid from there
                # round n down to nearest divisor d: n - (n % d)
                # (grid_x0 / grid_y0 in local coordinates btw)
                grid_size = 50
                grid_x0 = int(self.offset[0] - (self.offset[0] % grid_size))
                grid_x1 = int(grid_x0 + self.size[0] + grid_size)
                grid_y0 = int(self.offset[1] - (self.offset[1] % grid_size))
                grid_y1 = int(grid_y0 + self.size[1] + grid_size)
                for x in range(grid_x0, grid_x1, grid_size):
                    draw_list.add_line(self.local_to_screen((x, grid_y0)), self.local_to_screen((x, grid_y1)), COLOR_EDITOR_GRID)
                for y in range(grid_y0, grid_y1, grid_size):
                    draw_list.add_line(self.local_to_screen((grid_x0, y)), self.local_to_screen((grid_x1,  y)), COLOR_EDITOR_GRID)

            for node in self.nodes:
                node.show(draw_list)
            for connection in self.connections:
                connection.show(draw_list)

            # dropping connection to ports is handled by nodes
            # we're checking here if a connection was dropped into nowhere
            if self.dragging_connection is not None and imgui.is_mouse_released(0):
                self.dragging_connection.disconnect()
                self.connections.remove(self.dragging_connection)
                self.dragging_connection = None

            if self.dragging_connection is None and imgui.is_mouse_clicked(0):
                self.dragging_position = True
            if self.dragging_position:
                self.offset = t_sub(self.offset, imgui.get_mouse_drag_delta())
                imgui.reset_mouse_drag_delta()
            if self.dragging_position and imgui.is_mouse_released(0):
                self.dragging_position = False

            imgui.text("I'm expanded!")
            imgui.text("offset: %d %d" % self.offset)

            if imgui.is_mouse_clicked(1) and imgui.is_window_hovered() \
                    and not any(map(lambda n: n.hovered, self.nodes)):
                imgui.open_popup("context")
            if imgui.begin_popup("context"):
                if imgui.menu_item("TestNode")[0]:
                    pos = io.mouse_pos
                    self.nodes.append(Node(self, pos=self.screen_to_local(pos)))
                for name in ["FooNode", "BlahNode"]:
                    imgui.menu_item(name)
                imgui.separator()
                if imgui.begin_menu("More Nodes"):
                    imgui.menu_item("AnotherNode")
                    imgui.end_menu()
                imgui.separator()
                if imgui.menu_item("reset offset")[0]:
                    self.offset = (0, 0)
                imgui.end_popup()
            draw_list.channels_merge()
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
