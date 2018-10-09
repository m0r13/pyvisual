#!/usr/bin/env python3

import sys
import time
from vispy import app, gloo, keys
import vispy.ext.glfw as glfw
import imgui

from pyvisual.editor import vispy_imgui

# TODO the naming here?
import pyvisual.node as node_meta
import pyvisual.editor.widget as node_widget

# create canvas / opengl context already here
# imgui seems to cause problems otherwise with imgui.get_color_u32_rgba without context
canvas = app.Canvas(keys=None, vsync=False, autoswap=True)
timer = app.Timer(1.0 / 30.0, connect=canvas.update, start=True)
imgui_renderer = vispy_imgui.GlumpyGlfwRenderer(canvas.native, True)

# utilities
# TODO replace them with ImVec2 implementation in pyimgui bindings
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

def t_overlap(a_start, a_end, b_start, b_end):
    # check if the rects a and b overlap
    # https://stackoverflow.com/a/306332
    # if (RectA.Left < RectB.Right && RectA.Right > RectB.Left &&
    #             RectA.Top > RectB.Bottom && RectA.Bottom < RectB.Top ) 
    return a_start[0] < b_end[0] and a_end[0] > b_start[0] and \
            a_start[1] < b_end[1] and a_end[1] > b_start[1]

def round_next(n, d):
    return n - (n % d)

COLOR_EDITOR_BACKGROUND = imgui.get_color_u32_rgba(0.1, 0.1, 0.1, 1.0)
COLOR_EDITOR_GRID = imgui.get_color_u32_rgba(0.3, 0.3, 0.3, 1.0)
COLOR_NODE_BACKGROUND = imgui.get_color_u32_rgba(0.0, 0.0, 0.0, 1.0)
COLOR_NODE_BORDER = imgui.get_color_u32_rgba(0.7, 0.7, 0.7, 1.0)
COLOR_NODE_BORDER_HOVERED = imgui.get_color_u32_rgba(1.0, 1.0, 1.0, 0.5)
COLOR_NODE_BORDER_SELECTED = imgui.get_color_u32_rgba(1.0, 0.697, 0.0, 0.5)

COLOR_PORT_HIGHLIGHT_POSITIVE = imgui.get_color_u32_rgba(0.0, 0.5, 0.0, 1.0)
COLOR_PORT_HIGHLIGHT_POSITIVE_ACTIVE = imgui.get_color_u32_rgba(0.5, 0.5, 0.0, 1.0)
COLOR_PORT_HIGHLIGHT_NEUTRAL = imgui.get_color_u32_rgba(0.0, 0.0, 0.0, 0.0)
COLOR_PORT_HIGHLIGHT_NEGATIVE = imgui.get_color_u32_rgba(0.5, 0.5, 0.5, 0.5)
COLOR_PORT_BULLET = imgui.get_color_u32_rgba(1.0, 0.0, 0.0, 1.0)
COLOR_PORT_BULLET_HOVERED = imgui.get_color_u32_rgba(1.0, 1.0, 0.0, 1.0)
COLOR_PORT_BULLET_DROPPABLE = imgui.get_color_u32_rgba(0.0, 1.0, 0.0, 1.0)
COLOR_PORT_BULLET_DISABLED = COLOR_NODE_BORDER

COLOR_SELECTION = imgui.get_color_u32_rgba(1.0, 0.697, 0.0, 0.3)
COLOR_SELECTION_BORDER = imgui.get_color_u32_rgba(1.0, 0.697, 0.0, 0.8)

CHANNEL_BACKGROUND = 0
CHANNEL_DEFAULT = 1
CHANNEL_NODE_BACKGROUND = 3
CHANNEL_NODE = 4
CHANNEL_CONNECTION = 5
CHANNEL_PORT = 2
CHANNEL_SELECTION = 6
CHANNEL_COUNT = 7

EDITOR_GRID_SIZE = 50
EDITOR_NODE_GRID_SIZE = 5

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

        p0 = self.input_node.get_port_position(PORT_TYPE_OUTPUT, self.input_index)
        p1 = self.output_node.get_port_position(PORT_TYPE_INPUT, self.output_index)

        delta = p1[0] - p0[0], p1[1] - p0[1]
        offset_x = min(200, abs(delta[0])) * 0.5
        offset_y = 0
        if delta[0] < 0:
            offset_x = min(200, 0.5 * abs(delta[0]))
            offset_y = min(100, abs(delta[1]))
        b0 = t_add(p0, (offset_x, offset_y))
        b1 = t_add(p1, (-offset_x, -offset_y))
        with draw_on_channel(draw_list, CHANNEL_CONNECTION):
            draw_list.add_bezier_curve(p0, b0, b1, p1, color, 2.0)
            # visualize the control points
            #draw_list.add_circle_filled(b0, 3, imgui.get_color_u32_rgba(0.0, 1.0, 0.0, 1.0))
            #draw_list.add_circle_filled(b1, 3, imgui.get_color_u32_rgba(0.0, 0.0, 1.0, 1.0))

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
    def __init__(self, editor, spec, pos=(100, 100)):
        self.editor = editor
        self.spec = spec

        self.window_id = Node.id_counter
        Node.id_counter += 1

        # TODO maybe this can be somehow better, idk
        # at the moment inputs/outputs have separate data structures
        # maybe something shared would be possible with proper port IDs
        inputs = self.spec.inputs
        outputs = self.spec.outputs
        self.ports = (inputs, outputs)
        self.port_positions = ([None]*len(inputs), [None]*len(outputs))
        self.port_widgets = ([None]*len(inputs), [None]*len(outputs))
        self.connections = ([[] for _ in inputs], [[] for _ in outputs])

        # initialize port widgets
        def create_widgets(ports, widgets):
            assert len(ports) == len(widgets)
            for i, port_spec in enumerate(ports):
                widgets[i] = node_widget.ImGuiValue.create(port_spec)
        create_widgets(self.spec.inputs, self.port_widgets[PORT_TYPE_INPUT])
        create_widgets(self.spec.outputs, self.port_widgets[PORT_TYPE_OUTPUT])

        #
        # size information of node (everything in local position)
        #
        self.padding = 5, 5
        self.pos = pos
        self.size = 10, 10

        #
        # state of node
        #
        self.collapsible = self.spec.options["show_title"]
        self.collapsed = False
        # is this node being dragged?
        # note: - for dragging selections of nodes, only the handle (clicked) node is marked as dragging
        #       - all others get dragging_from set
        self.dragging = False
        # if this node is the handle: where was mouse at beginning of drag operation (screen pos)
        self.dragging_mouse_start = None
        # where was this node at the beginning of drag operation? (local pos)
        self.dragging_node_start = None
        self.hovered = False
        self.selected = False

        #
        # associated node instance
        #
        self._instance = None

    @property
    def actual_pos(self):
        # local pos with node grid applied
        if EDITOR_NODE_GRID_SIZE > 1.0:
            return round_next(self.pos[0], EDITOR_NODE_GRID_SIZE), round_next(self.pos[1], EDITOR_NODE_GRID_SIZE)
        else:
            return self.pos

    @property
    def size_with_padding(self):
        return t_add(self.size, t_mul(self.padding, 2))

    def attach_connection(self, port_type, port_index, connection):
        self.connections[port_type][port_index].append(connection)

    def detach_connection(self, port_type, port_index, connection):
        self.connections[port_type][port_index].remove(connection)

    def get_port_position(self, port_type, port_index):
        positions = self.port_positions[port_type]
        # handle collapsed node
        if self.collapsed or port_index >= len(positions) or positions[port_index] is None:
            x = self.actual_pos[0] if port_type == PORT_TYPE_INPUT else self.actual_pos[0]+self.size[0]+self.padding[0]*2
            y = self.actual_pos[1] + (self.size[1] + self.padding[1] * 2) / 2
            return self.editor.local_to_screen((x, y))
        return positions[port_index]

    def show_port(self, draw_list, port_type, port_index, port_spec):
        io = imgui.get_io()

        name = port_spec["name"]
        dtype = port_spec["dtype"]

        # ui
        imgui.push_id(port_index)
        imgui.begin_group()

        # screen coordinates
        port_start = imgui.get_cursor_screen_pos()

        # show port label (if enabled)
        if port_spec["show_label"]:
            label = "%s > %s" % (dtype, name) 
            if port_type == PORT_TYPE_OUTPUT:
                label = "%s > %s" % (name, dtype)
            imgui.text(label)

        # show port input/output widget (if enabled)
        widget = self.port_widgets[port_type][port_index]
        if widget is not None:
            # determine value associated with this port
            value = None
            # and whether we can change it
            read_only = False
            if port_type == PORT_TYPE_INPUT:
                # we can change value of input port only if nothing is connected
                # otherwise it's a read-only widget that just shows the value for the user
                value = self.instance.inputs[name]
                if isinstance(value, node_meta.InputValueHolder):
                    if value.is_connected:
                        read_only = True
                    else:
                        value = value.manual_value
            else:
                value = self.instance.outputs[name]
            widget.show(value, read_only=read_only)
        imgui.end_group()

        # got the area our port takes up now
        # from port_start to port_end (both screen coordinates)
        port_end = imgui.get_item_rect_max()

        # calculate position and size of port connector
        size = imgui.get_item_rect_size()
        x = self.actual_pos[0]
        if port_type == PORT_TYPE_OUTPUT:
            x += self.size[0] + self.padding[0]*2
        y = self.editor.screen_to_local(port_start)[1] + size[1] / 2
        connector_radius = 5.0
        connector_thickness = 2.0
        connector_center = self.editor.local_to_screen((x, y))
        self.port_positions[port_type][port_index] = connector_center

        # find connector bounds for hovering
        # they are a bit bigger than the actual connector
        connector_start, connector_end = None, None
        if port_type == PORT_TYPE_INPUT:
            connector_start = t_add(port_start, (-30, 0))
            connector_end = port_start[0], port_end[1]
        else:
            connector_start = port_end[0], port_start[1]
            connector_end = t_add(port_end, (30, 0))

        # state of port / connector
        is_dragging_connection = self.editor.is_dragging_connection()
        is_connection_droppable = False
        if is_dragging_connection:
            is_connection_droppable = self.editor.is_connection_droppable(self, port_type, port_index)
        # whether this port is part of a dragging connection
        is_connection_source = self.editor.is_dragging_connection_source(self, port_type, port_index)
        connections = self.connections[port_type][port_index]
        # constraint: make sure there is maximum one connection per input
        if port_type == PORT_TYPE_INPUT:
            assert len(connections) in (0, 1)

        hovered_port = t_between(port_start, port_end, io.mouse_pos)
        hovered_connector = t_between(connector_start, connector_end, io.mouse_pos)
        hovered = hovered_connector or hovered_port

        # decide port bullet color
        bullet_color = COLOR_PORT_BULLET
        if is_dragging_connection and is_connection_source:
            # connection source is drawn as hovered
            bullet_color = COLOR_PORT_BULLET_HOVERED
        elif is_dragging_connection and not is_connection_droppable:
            # any port where it's not is_connection_droppable is disabled
            bullet_color = COLOR_PORT_BULLET_DISABLED
        elif hovered_connector or (is_dragging_connection and hovered_port):
            bullet_color = COLOR_PORT_BULLET_HOVERED
        elif is_dragging_connection and is_connection_droppable:
            bullet_color = COLOR_PORT_BULLET_DROPPABLE

        # decide port highlight color
        highlight_channel = CHANNEL_NODE_BACKGROUND
        highlight_color = COLOR_PORT_HIGHLIGHT_NEUTRAL
        if is_dragging_connection and not is_connection_source:
            if not is_connection_droppable:
                highlight_channel = CHANNEL_NODE
                highlight_color = COLOR_PORT_HIGHLIGHT_NEGATIVE
            else:
                highlight_channel = CHANNEL_NODE_BACKGROUND
                highlight_color = COLOR_PORT_HIGHLIGHT_POSITIVE

        # decide for action on port / port bullet
        deleteable = port_type == PORT_TYPE_INPUT and len(connections) > 0
        if hovered_connector and deleteable and not is_dragging_connection:
            imgui.set_tooltip("Delete connection")
            if imgui.is_mouse_clicked(0):
                self.editor.remove_connection(connections[0])
                # little tweak: start dragging a new connection once a connection is deleted
                self.editor.drag_connection(self, port_type, port_index)
        elif hovered and is_dragging_connection and is_connection_droppable:
            highlight_channel = CHANNEL_NODE_BACKGROUND
            highlight_color = COLOR_PORT_HIGHLIGHT_POSITIVE_ACTIVE
            imgui.set_tooltip("Drop connection")
            if imgui.is_mouse_released(0):
                self.editor.drop_connection(self, port_type, port_index)
        elif not is_dragging_connection and hovered_connector:
            imgui.set_tooltip("Create connection")
            if imgui.is_mouse_clicked(0):
                self.editor.drag_connection(self, port_type, port_index)

        # port connector drawing
        with draw_on_channel(draw_list, CHANNEL_PORT):
            if len(connections) > 0:
                draw_list.add_circle_filled(connector_center, connector_radius, bullet_color)
            else:
                draw_list.add_circle(connector_center, connector_radius, bullet_color, 12, connector_thickness)

        # port highlight drawing
        with draw_on_channel(draw_list, highlight_channel):
            draw_list.add_rect_filled(port_start, port_end, highlight_color)

        imgui.pop_id()

    def show_ports(self, draw_list, ports, port_type):
        io = imgui.get_io()

        channel_stack = draw_on_channel(draw_list, CHANNEL_NODE)
        channel_stack.__enter__()

        imgui.push_id(int(port_type))
        imgui.begin_group()
        for port_index, port_spec in enumerate(ports):
            self.show_port(draw_list, port_type, port_index, port_spec)
        imgui.end_group()
        imgui.pop_id()

        channel_stack.__exit__()

    def show(self, draw_list):
        io = imgui.get_io()

        channel_stack = draw_on_channel(draw_list, CHANNEL_NODE)
        channel_stack.__enter__()

        imgui.push_id(self.window_id)
        old_cursor_pos = imgui.get_cursor_pos()

        # calculate position of drag operation first
        # TODO: this causes a frame delay for nodes that are rendered before this
        # maybe it's fixable without too much effort
        if self.dragging:
            assert self.selected
            assert self.dragging_mouse_start is not None
            delta = t_sub(self.dragging_mouse_start, io.mouse_pos)
            for node in self.editor.nodes:
                if node.selected:
                    # pos = old pos + delta
                    node.pos = t_sub(node.dragging_node_start, delta)

        # draw background
        upper_left = self.editor.local_to_screen(self.actual_pos)
        lower_right = t_add(upper_left, self.size_with_padding)
        with draw_on_channel(draw_list, CHANNEL_NODE_BACKGROUND):
            draw_list.add_rect_filled(upper_left, lower_right, COLOR_NODE_BACKGROUND, 5.0)

        # draw content of node
        # (set_cursor_pos is window coordinates)
        imgui.set_cursor_pos(self.editor.local_to_window(t_add(self.actual_pos, self.padding)))
        imgui.begin_group()
        if self.spec.options["show_title"]:
            imgui.text(self.spec.name)
        if not self.collapsed:
            if len(self.spec.inputs):
                imgui.begin_group()
                self.show_ports(draw_list, self.spec.inputs, PORT_TYPE_INPUT)
                imgui.end_group()
                imgui.same_line()

            if len(self.spec.outputs):
                imgui.begin_group()
                self.show_ports(draw_list, self.spec.outputs, PORT_TYPE_OUTPUT)
                imgui.end_group()
        imgui.end_group()

        # update known size of the node
        self.size = imgui.get_item_rect_size()

        # some bounds for hovering / selection highlighting
        # and check if we're actually hovered
        padding_hover = (4, 4)
        padding_selection = (6, 6)
        upper_left = self.editor.local_to_screen(self.actual_pos)
        upper_left_hover = t_sub(upper_left, padding_hover)
        upper_left_selection = t_sub(upper_left, padding_selection)
        lower_right = t_add(upper_left, self.size_with_padding)
        lower_right_hover = t_add(lower_right, padding_hover)
        lower_right_selection = t_add(lower_right, padding_selection)
        self.hovered = imgui.is_window_hovered() and t_between(upper_left_selection, lower_right_selection, io.mouse_pos)

        # handle clicks / scrolling on the node
        if not self.editor.is_dragging_connection() and self.hovered and not imgui.is_any_item_active():
            # handle collapsing/expanding
            if self.collapsible:
                if self.collapsed and io.mouse_wheel < 0:
                    self.collapsed = False
                elif not self.collapsed and io.mouse_wheel > 0:
                    self.collapsed = True
            # handle selection
            if imgui.is_mouse_clicked(0):
                # ctrl modifier toggles selection
                if io.key_ctrl:
                    self.selected = not self.selected
                # otherwise select only this node
                else:
                    for node in self.editor.nodes:
                        node.selected = False
                    self.selected = True
            # handle context menu
            if imgui.is_mouse_clicked(1):
                # little hack to have first context menu entry under cursor
                pos = io.mouse_pos
                io.mouse_pos = t_add(pos, (-20, -20))
                imgui.open_popup("context")
                io.mouse_pos = pos

        # draw context menu (if opened)
        if imgui.begin_popup("context"):
            if imgui.menu_item("delete")[0]:
                self.editor.remove_node(self)
            if imgui.menu_item("expand..." if self.collapsed else "collaps...")[0]:
                self.collapsed = not self.collapsed
            imgui.end_popup()

        # handle clicking the node once it's selected as dragging
        if self.hovered and imgui.is_mouse_clicked(0) \
                and self.selected and not self.editor.is_dragging_connection():
            # mark this node as being dragged
            self.dragging = True
            self.dragging_mouse_start = io.mouse_pos
            # set for all selected nodes where they were at beginning of dragging
            for node in self.editor.nodes:
                if node.selected:
                    node.dragging_node_start = self.editor.local_to_screen(node.actual_pos)
        # stop dragging once mouse is released again
        if self.dragging and imgui.is_mouse_released(0):
            self.dragging = False
            self.dragging_mouse_start = None
            for node in self.editor.nodes:
                node.dragging_node_start = None

        # draw border(s)
        with draw_on_channel(draw_list, CHANNEL_NODE_BACKGROUND):
            draw_list.add_rect(upper_left, lower_right, COLOR_NODE_BORDER, 2.0)
            if self.hovered:
                draw_list.add_rect(upper_left_hover, lower_right_hover, COLOR_NODE_BORDER_HOVERED, 2.0)
            if self.selected:
                draw_list.add_rect(upper_left_selection, lower_right_selection, COLOR_NODE_BORDER_SELECTED, 2.0)

        imgui.pop_id()
        imgui.set_cursor_pos(old_cursor_pos)

        channel_stack.__exit__()

    @property
    def instance(self):
        if self._instance is None:
            self._instance = self.spec.cls()
        return self._instance

class NodeEditor:
    def __init__(self, node_specs):
        # available nodes for this editor
        self.node_specs = node_specs

        # collection of ui nodes/connections
        self.nodes = []
        self.connections = []

        # window position in screen space
        self.pos = (0, 0)
        self.size = (1, 1)
        # offset for dragging position around
        # offset (100, 100) means that at window (0, 0) is local position (100, 100)
        self.offset = (0, 0)

        # interaction state
        # if user is dragging a connection: this is the ui connection object
        self.dragging_connection = None
        self.dragging_target_port_type = None
        # whether user is dragging position
        self.dragging_position = False
        # whether user is making a selection
        self.dragging_selection = False
        self.selection_start = None
        # save position where context menu was opened
        # (for spawning nodes exactly where menu was opened)
        self.context_mouse_pos = None

        # performance measurement stuffs
        self.fps = 0.0
        self.editor_time = 0.0
        self.editor_time_relative = 0.0
        self.processing_time = 0.0
        self.processing_time_relative = 0.0
        self.show_test_window = False

    #
    # coordinate conversions
    #
    def local_to_window(self, pos):
        return t_sub(pos, self.offset)
    def local_to_screen(self, pos):
        return t_sub(t_add(self.pos, pos), self.offset)
    def screen_to_local(self, pos):
        return t_add(t_sub(pos, self.pos), self.offset)

    #
    # editor api functions used by nodes, connections and editor itself
    #
    
    def remove_node(self, node):
        print("removing node %s" % node.spec.name)
        for port_type in (PORT_TYPE_INPUT, PORT_TYPE_OUTPUT):
            for port_connections in node.connections[port_type]:
                # the list of connections at this port will change during deletetion!
                # that's why we iterate of a copy
                for connection in list(port_connections):
                    self.remove_connection(connection)
        self.nodes.remove(node)

    def remove_connection(self, connection):
        # remove connection from node instances
        dst_instance = connection.output_node.instance
        dst_name = connection.output_node.ports[PORT_TYPE_INPUT][connection.output_index]["name"]
        dst_instance.inputs[dst_name].disconnect()

        # remove connection ui-wise
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
        if port_type == PORT_TYPE_INPUT \
                and len(node.connections[PORT_TYPE_INPUT][port_index]) != 0:
            return False
        # TODO this is hacky too
        port_spec = node.ports[port_type][port_index]
        connection = self.dragging_connection
        other_port_spec = None
        if port_type == PORT_TYPE_INPUT:
            other_port_spec = connection.input_node.ports[PORT_TYPE_OUTPUT][connection.input_index]
        else:
            other_port_spec = connection.output_node.ports[PORT_TYPE_INPUT][connection.output_index]
        return port_spec["dtype"] == other_port_spec["dtype"]

    def drop_connection(self, node, port_type, port_index):
        assert self.is_dragging_connection()
        assert self.is_connection_droppable(node, port_type, port_index)

        # connect ui nodes
        connection = self.dragging_connection
        connection.disconnect()
        if port_type == PORT_TYPE_INPUT:
            connection.output_node = node
            connection.output_index = port_index
        else:
            connection.input_node = node
            connection.input_index = port_index
        connection.connect()
        self.dragging_connection = None

        # connect node instances
        src_instance = connection.input_node.instance
        src_name = connection.input_node.ports[PORT_TYPE_OUTPUT][connection.input_index]["name"]
        dst_instance = connection.output_node.instance
        dst_name = connection.output_node.ports[PORT_TYPE_INPUT][connection.output_index]["name"]
        dst_instance.inputs[dst_name].connect(src_instance, src_name)

    #
    # functions for accessing graph of node instances
    # TODO maybe move this out of editor?
    # 

    @property
    def node_instances(self):
        return map(lambda node: node.instance, self.nodes)

    @property
    def node_instances_sorted(self):
        instances = list(self.node_instances)
        visited_instances = set()
        sorted_instances = list()
        circular = False

        def dfs(instance):
            nonlocal visited_instances, circular
            if instance in visited_instances:
                return
            visited_instances.add(instance)
            for instance_before in instance.input_nodes:
                #if instance_before in visited_instances:
                #    circular = True
                dfs(instance_before)
            sorted_instances.append(instance)

        for instance in instances:
            dfs(instance)
        return sorted_instances, circular

    #
    # misc stuff
    #

    def fps_callback(self, fps):
        self.fps = fps

    def timing_callback(self, editor_time, processing_time):
        self.editor_time = editor_time
        self.editor_time_relative = editor_time / (1.0 / self.fps)
        self.processing_time = processing_time
        self.processing_time_relative = processing_time / (1.0 / self.fps)

    #
    # rendering and interaction handling
    #

    def get_selection(self):
        # returns selection bounds as rect (start, end)
        # local coords!
        # if there is no selection, returns None
        if not self.dragging_selection:
            return None
        assert self.selection_start is not None
        a = self.selection_start
        b = self.screen_to_local(imgui.get_io().mouse_pos)
        start = min(a[0], b[0]), min(a[1], b[1])
        end = max(a[0], b[0]), max(a[1], b[1])
        return start, end

    def update_node_selection(self, selection_start, selection_end):
        # easy: check if selection and each node overlap
        # (selection is in local coords, just like nodes)
        for node in self.nodes:
            node_start = node.actual_pos
            node_end = t_add(node.actual_pos, node.size_with_padding)
            node.selected = t_overlap(selection_start, selection_end, node_start, node_end)

    def show(self):
        # create editor window
        io = imgui.get_io()
        w, h = io.display_size
        imgui.set_next_window_position(0, 0)
        imgui.set_next_window_size(w, h)

        flags = imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_BRING_TO_FRONT_ON_FOCUS
        expanded, _ = imgui.begin("NodeEditor", False, flags)
        self.pos = imgui.get_window_position()
        self.size = imgui.get_window_size()
        if not expanded:
            pass

        # main menu bar
        imgui.begin_main_menu_bar()
        if imgui.begin_menu("File", True):
            imgui.menu_item("New", "Ctrl+N", False, True)
            imgui.menu_item("Open...", "Ctrl+O", False, True)
            imgui.menu_item("Save", "Ctrl+S", False, True)
            imgui.menu_item("Save as...", "Shift+Ctrl+S", False, True)
            imgui.end_menu()
        imgui.end_main_menu_bar()
        imgui.begin_main_menu_bar()
        if imgui.begin_menu("blah", True):
            imgui.menu_item("New", "Ctrl+N", False, True)
            imgui.end_menu()
        imgui.end_main_menu_bar()

        # initialize draw list
        draw_list = imgui.get_window_draw_list()
        draw_list.channels_split(CHANNEL_COUNT)
        draw_list.channels_set_current(CHANNEL_DEFAULT)

        # draw grid
        with draw_on_channel(draw_list, CHANNEL_BACKGROUND):
            draw_list.add_rect_filled(self.pos, t_add(self.pos, self.size), COLOR_EDITOR_BACKGROUND)
            # how does the grid work?
            #   -> find local coords where we see first grid pos
            #   -> build grid from there
            # round n down to nearest divisor d: n - (n % d)
            # (grid_x0 / grid_y0 in local coordinates btw)
            grid_size = EDITOR_GRID_SIZE
            grid_x0 = int(self.offset[0] - (self.offset[0] % grid_size))
            grid_x1 = int(grid_x0 + self.size[0] + grid_size)
            grid_y0 = int(self.offset[1] - (self.offset[1] % grid_size))
            grid_y1 = int(grid_y0 + self.size[1] + grid_size)
            for x in range(grid_x0, grid_x1, grid_size):
                draw_list.add_line(self.local_to_screen((x, grid_y0)), self.local_to_screen((x, grid_y1)), COLOR_EDITOR_GRID)
            for y in range(grid_y0, grid_y1, grid_size):
                draw_list.add_line(self.local_to_screen((grid_x0, y)), self.local_to_screen((grid_x1,  y)), COLOR_EDITOR_GRID)

        # handle selection
        if self.dragging_selection:
            # update selected nodes
            selection_start, selection_end = self.get_selection()
            self.update_node_selection(selection_start, selection_end)

            # and draw selection
            with draw_on_channel(draw_list, CHANNEL_SELECTION):
                upper_left = self.local_to_screen(selection_start)
                lower_right = self.local_to_screen(selection_end)
                draw_list.add_rect_filled(upper_left, lower_right, COLOR_SELECTION)
                draw_list.add_rect(upper_left, lower_right, COLOR_SELECTION_BORDER)

        # draw / handle nodes and connections
        for node in self.nodes:
            node.show(draw_list)
        for connection in self.connections:
            connection.show(draw_list)

        # dropping connection to ports is handled by nodes
        # we're checking here if a connection was dropped into nowhere
        if self.is_dragging_connection() and imgui.is_mouse_released(0):
            self.dragging_connection.disconnect()
            self.connections.remove(self.dragging_connection)
            self.dragging_connection = None

        # handle a starting selection
        # it's important that ctrl is not pressed (ctrl is for dragging position)
        # and that no node is being dragged
        no_node_dragging = lambda: not any([ node.dragging for node in self.nodes])
        if imgui.is_window_hovered() and not self.is_dragging_connection() \
                and imgui.is_mouse_clicked(0) and not io.key_ctrl \
                and no_node_dragging():
            self.dragging_selection = True
            self.selection_start = self.screen_to_local(io.mouse_pos)

        # handle ending selection
        if self.dragging_selection and imgui.is_mouse_released(0):
            self.dragging_selection = False

        # handle different selection and node modifications for some shortcuts
        if imgui.is_window_hovered() and not imgui.is_any_item_active():
            key_map = list(io.key_map)
            key_a = key_map[imgui.KEY_A]
            key_d = glfw.GLFW_KEY_D
            key_i = glfw.GLFW_KEY_I
            key_escape = key_map[imgui.KEY_ESCAPE]
            key_delete = key_map[imgui.KEY_DELETE]
            keys_down = list(io.keys_down)
            if keys_down[key_a]:
                for node in list(self.nodes):
                    node.selected = True
            # TODO when we can detect when key was released (so this gets triggered only once)
            #if list(io.keys_down)[key_i]:
            #    for node in list(self.nodes):
            #        node.selected = not node.selected
            if keys_down[key_escape]:
                for node in list(self.nodes):
                    node.selected = False
            if keys_down[key_delete] or list(io.keys_down)[key_d]:
                for node in list(self.nodes):
                    if node.selected:
                        self.remove_node(node)

            # handle start dragging position with ctrl+click
            if not self.is_dragging_connection() \
                    and io.key_ctrl and imgui.is_mouse_clicked(0):
                self.dragging_position = True
        # update position
        if self.dragging_position:
            self.offset = t_sub(self.offset, imgui.get_mouse_drag_delta())
            imgui.reset_mouse_drag_delta()
        # end of dragging position
        if self.dragging_position and imgui.is_mouse_released(0):
            self.dragging_position = False

        # navbar is in place
        imgui.dummy(1, 12)
        imgui.text("fps: %.2f" % self.fps)
        imgui.text("editor time: %.2f ms ~ %.2f%%" % (self.editor_time * 1000.0, self.editor_time_relative * 100.0))
        imgui.text("processing time: %.2f ms ~ %.2f%%" % (self.processing_time * 1000.0, self.processing_time_relative * 100.0))

        # gather "graph" of node instances
        imgui.text("")
        instances, circular = self.node_instances_sorted
        num_nodes = len(instances)
        num_connections = sum([ sum([ 1 if v.is_connected else 0 for v in node.inputs.values() ]) for node in instances ])
        imgui.text("#%d nodes, #%d connections" % (num_nodes, num_connections))
        imgui.text("instances sorted:")
        imgui.same_line()

        # evaluate nodes
        # TODO move this out or so
        processing_time = 0.0
        if circular:
            # TODO show a warning maybe
            pass
        else:
            imgui.text(" -> ".join([ instance.get_node_spec().name for instance in instances ]))

            start = time.time()
            for instance in instances:
                instance.evaluated = False
            for instance in instances:
                instance.evaluate()
            end = time.time()
            processing_time = end - start

        # context menu
        no_node_hovered = lambda: not any(map(lambda n: n.hovered, self.nodes))
        if imgui.is_mouse_clicked(1) and imgui.is_window_hovered() \
                and no_node_hovered():
            # have first menu entry under cursor
            self.context_mouse_pos = io.mouse_pos
            io.mouse_pos = t_add(self.context_mouse_pos, (-20, -20))
            imgui.open_popup("context")
            io.mouse_pos = self.context_mouse_pos
        if imgui.begin_popup("context"):
            assert self.context_mouse_pos is not None
            for i, spec in enumerate(self.node_specs):
                imgui.push_id(i)
                label = spec.name
                if spec.options["category"]:
                    label += " (%s)" % spec.options["category"]
                if imgui.menu_item(label)[0]:
                    pos = self.screen_to_local(self.context_mouse_pos)
                    self.nodes.append(Node(self, spec, pos=pos))
                    # TODO it would be nice to set the mouse position back to where the node is now
                imgui.pop_id()
            imgui.separator()
            clicked, self.show_test_window = imgui.menu_item("show demo window", None, self.show_test_window)
            if clicked:
                imgui.set_window_focus("ImGui Demo")
            if imgui.menu_item("reset offset")[0]:
                self.offset = (0, 0)
            imgui.end_popup()

        # finish our drawing
        draw_list.channels_merge()

        if self.show_test_window:
            imgui.show_test_window()
        imgui.end()

        # TODO this is a bit hacky, handle this differently
        return processing_time

# sort by node categories and then by names
node_types = node_meta.VisualNode.get_sub_nodes(include_self=False)
node_types.sort(key=lambda n: n.get_node_spec().name)
node_types.sort(key=lambda n: n.get_node_spec().options["category"])

# TODO think about naming
#   ui nodes vs. node instances vs. node types
node_specs = [ n.get_node_spec() for n in node_types ]
editor = NodeEditor(node_specs)

editor_time = 0.0
processing_time = 0.0
time_count = 0

@canvas.connect
def on_draw(event):
    global editor_time, processing_time, time_count

    gloo.set_clear_color((0.2, 0.4, 0.6, 1.0))
    # TODO why does gloo.clear not work?
    #gloo.clear(depth=True, color=True)
    gloo.gl.glClear(gloo.gl.GL_COLOR_BUFFER_BIT)

    start = time.time()
    imgui_renderer.process_inputs()
    imgui.new_frame()

    # TODO hmm this is not so nice
    processing_time += editor.show()

    imgui.render()
    draw = imgui.get_draw_data()
    imgui_renderer.render(draw)

    editor_time += time.time() - start - processing_time
    time_count += 1
    if time_count >= 30:
        editor.timing_callback(editor_time / time_count, processing_time / time_count)
        editor_time = 0.0
        processing_time = 0.0
        time_count = 0

@canvas.connect
def on_key_press(event):
    if event.key == "q":
        sys.exit(0)

if __name__ == "__main__":
    canvas.show()
    canvas.measure_fps(1, editor.fps_callback)
    app.run()
