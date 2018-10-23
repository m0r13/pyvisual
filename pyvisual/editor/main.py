#!/usr/bin/env python3

import os
import sys
import time
import contextlib
from collections import defaultdict
from glumpy import app, gloo, gl
from glumpy.ext import glfw
import imgui

from pyvisual.editor import glumpy_imgui

# TODO the naming here?
import pyvisual.node as node_meta
import pyvisual.editor.widget as node_widget
import pyvisual.node.dtype as node_dtype
from pyvisual.editor.graph import NodeGraph
from pyvisual import assets

import cProfile
profile = cProfile.Profile()

# create window / opengl context already here
# imgui seems to cause problems otherwise with imgui.get_color_u32_rgba without context
window = app.Window()
app.clock.get_default().set_fps_limit(30)
imgui_renderer = glumpy_imgui.GlumpyGlfwRenderer(window, True)

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

def t_cull(node_start, node_end):
    io = imgui.get_io()
    screen_start = (0, 0)
    screen_end = io.display_size
    if not t_overlap(screen_start, screen_end, node_start, node_end):
        return True
    return False

def round_next(n, d):
    return n - (n % d)

def is_substring_partly(substring, string):
    # returns if substring is a substring of string,
    # where characters in string can be skipped
    # example: "infloat" is in "inputfloat"

    # empty substring always contained
    if not substring:
        return True
    i = 0
    for c in string:
        if c == substring[i]:
            i += 1
            if i == len(substring):
                return True
    return i == len(substring)

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
COLOR_PORT_BULLET_HOVERED = imgui.get_color_u32_rgba(1.0, 1.0, 0.0, 1.0)
COLOR_PORT_BULLET_DROPPABLE = imgui.get_color_u32_rgba(0.0, 1.0, 0.0, 1.0)
COLOR_PORT_BULLET_DISABLED = COLOR_NODE_BORDER

_red = imgui.get_color_u32_rgba(0.8, 0.0, 0.0, 1.0)
_green = imgui.get_color_u32_rgba(0.0, 0.6, 0.0, 1.0)
_light_blue = imgui.get_color_u32_rgba(0.1, 0.6, 1.0, 1.0)
_yellow = imgui.get_color_u32_rgba(0.8, 0.8, 0.0, 1.0)
_orange = imgui.get_color_u32_rgba(0.8, 0.5, 0.0, 1.0)
_purpol = imgui.get_color_u32_rgba(0.6, 0.0, 0.6, 1.0)
_white = imgui.get_color_u32_rgba(0.7, 0.7, 0.7, 1.0)
_colors = {
    node_dtype.base_float : _green,
    node_dtype.base_str : _white,
    node_dtype.base_vec4 : _red,
    node_dtype.base_mat4 : _purpol,
    node_dtype.base_tex2d : _light_blue,
    node_dtype.base_audio : _orange,
}
def get_connection_color(dtype):
    return _colors.get(dtype.base_type, _white)

COLOR_SELECTION = imgui.get_color_u32_rgba(1.0, 0.697, 0.0, 0.3)
COLOR_SELECTION_BORDER = imgui.get_color_u32_rgba(1.0, 0.697, 0.0, 0.8)

CHANNEL_BACKGROUND = 0
CHANNEL_DEFAULT = 1
CHANNEL_NODE_BACKGROUND = 3
CHANNEL_NODE = 4
CHANNEL_CONNECTION = 5
CHANNEL_PORT = 2
CHANNEL_PORT_LABEL = 6
CHANNEL_SELECTION = 7
CHANNEL_COUNT = 8

EDITOR_GRID_SIZE = 50
EDITOR_NODE_GRID_SIZE = 5

#class draw_on_channel:
#    def __init__(self, draw_list, channel):
#        self.draw_list = draw_list
#        self.old_channel = None
#        self.new_channel = channel
#
#    def __enter__(self):
#        self.old_channel = self.draw_list.channels_current
#        self.draw_list.channels_set_current(self.new_channel)
#    def __exit__(self, *args):
#        assert self.old_channel is not None
#        self.draw_list.channels_set_current(self.old_channel)
#        return False

@contextlib.contextmanager
def draw_on_channel(draw_list, channel):
    old_channel = draw_list.channels_current
    draw_list.channels_set_current(channel)

    yield

    draw_list.channels_set_current(old_channel)

class Connection:
    def __init__(self, editor, src_node, src_port_id, dst_node, dst_port_id):
        self.editor = editor
        self.src_node = src_node
        self.src_port_id = src_port_id
        self.dst_node = dst_node
        self.dst_port_id = dst_port_id
        self.connect()

    def connect(self):
        self.src_node.attach_connection(self.src_port_id, self)
        self.dst_node.attach_connection(self.dst_port_id, self)

    def disconnect(self):
        self.src_node.detach_connection(self.src_port_id, self)
        self.dst_node.detach_connection(self.dst_port_id, self)

    def show(self, draw_list):
        # is connected when both sides are on a node
        connected = not isinstance(self.src_node, MouseDummyNode) \
                and not isinstance(self.dst_node, MouseDummyNode)
        dragging_connection = self.editor.is_dragging_connection()

        color = None
        if dragging_connection and connected:
            # show connections while other connection is dragged as inactive
            color = COLOR_PORT_BULLET_DISABLED
        elif dragging_connection and not connected:
            # show connection that is being dragged as active
            color = COLOR_PORT_BULLET_HOVERED
        else:
            dtype = None
            if self.src_port_id is not None:
                dtype = self.src_node.instance.ports[self.src_port_id]["dtype"]
            elif self.dst_port_id is not None:
                dtype = self.dst_node.instance.ports[self.dst_port_id]["dtype"]
            else:
                assert False
            color = get_connection_color(dtype)

        p0 = self.src_node.get_port_position(self.src_port_id)
        p1 = self.dst_node.get_port_position(self.dst_port_id)

        delta = p1[0] - p0[0], p1[1] - p0[1]
        offset_x = min(200, abs(delta[0])) * 0.5
        offset_y = 0
        if delta[0] < 0:
            offset_x = min(200, 0.5 * abs(delta[0]))
            offset_y = min(100, abs(delta[1]))
        b0 = t_add(p0, (offset_x, offset_y))
        b1 = t_add(p1, (-offset_x, -offset_y))
        with draw_on_channel(draw_list, CHANNEL_CONNECTION):
            # simple lines
            #draw_list.add_line(p0, p1, color, 2.0)
            # fancy bezier
            draw_list.add_bezier_curve(p0, b0, b1, p1, color, 2.0)
            # visualize the control points
            #draw_list.add_circle_filled(b0, 3, imgui.get_color_u32_rgba(0.0, 1.0, 0.0, 1.0))
            #draw_list.add_circle_filled(b1, 3, imgui.get_color_u32_rgba(0.0, 0.0, 1.0, 1.0))

    def is_end(self, node, port_id):
        return (self.src_node == node and self.src_port_id == port_id) \
                or (self.dst_node == node and self.dst_port_id == port_id)

    @staticmethod
    def create(editor, node, port_id):
        if node_meta.is_input(port_id):
            return Connection(editor, dst_node=node, dst_port_id=port_id,
                    src_node=MouseDummyNode(), src_port_id=None)
        else:
            return Connection(editor, src_node=node, src_port_id=port_id,
                    dst_node=MouseDummyNode(), dst_port_id=None)

class MouseDummyNode:
    def attach_connection(self, *args):
        pass
    def detach_connection(self, *args):
        pass

    def get_port_position(self, port_id):
        return imgui.get_io().mouse_pos

class Node:
    id_counter = 0
    def __init__(self, editor, instance, ui_data):
        self.editor = editor
        self.instance = instance
        self.spec = instance.spec

        self.window_id = Node.id_counter
        self.z_index = editor.touch_z_index()
        Node.id_counter += 1

        self.port_positions = {}
        self.widgets = {}
        self.connections = defaultdict(lambda: [])

        #
        # size information of node (everything in local position)
        #
        self.padding = 5, 5
        self.pos = ui_data.get("pos", (0, 0))
        self.size = 10, 10

        #
        # state of node
        #
        self.collapsible = self.spec.options["show_title"]
        self.collapsed = ui_data.get("collapsed", False)
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

        # trigger update of ui data
        self.editor.node_ui_state_changed(self)

        self.io = imgui.get_io()

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

    def touch_z_index(self):
        self.z_index = self.editor.touch_z_index()

    def attach_connection(self, port_id, connection):
        self.connections[port_id].append(connection)

    def detach_connection(self, port_id, connection):
        self.connections[port_id].remove(connection)

    def get_widget(self, port_id):
        if not port_id in self.widgets:
            assert port_id in self.instance.ports, "Port %s must be in instance ports" % port_id
            port_spec = self.instance.ports[port_id]
            assert len(port_spec["widgets"]) in (0, 1), "Only up to one widget allowed for now"
            widget_func = port_spec["widgets"][0] if len(port_spec["widgets"]) else (lambda *args: None)
            self.widgets[port_id] = widget_func(self)
        return self.widgets[port_id]

    def get_port_position(self, port_id):
        assert port_id in self.instance.ports, "Port %s must be in instance ports" % port_id

        # handle collapsed node
        if self.collapsed or port_id not in self.port_positions:
            x = self.actual_pos[0] if node_meta.is_input(port_id) else self.actual_pos[0]+self.size[0]+self.padding[0]*2
            y = self.actual_pos[1] + (self.size[1] + self.padding[1] * 2) / 2
            return self.editor.local_to_screen((x, y))
        return self.editor.local_to_screen(self.port_positions[port_id])

    def show_port(self, draw_list, port_id, port_spec):
        #profile.enable()

        io = self.io

        if port_spec["hide"]:
            return
        name = port_spec["name"]
        dtype = port_spec["dtype"]
        is_input = node_meta.is_input(port_id)

        # ui
        imgui.push_id(port_id)
        imgui.begin_group()

        # screen coordinates
        port_start = imgui.get_cursor_screen_pos()

        # show port input/output widget (if enabled)
        widget = self.get_widget(port_id)
        if widget is not None:
            # determine value associated with this port
            value = self.instance.get_value(port_id)
            # and whether we can change it
            read_only = False
            if is_input:
                # we can change value of input port only if nothing is connected
                # otherwise it's a read-only widget that just shows the value for the user
                if isinstance(value, node_meta.InputValueHolder):
                    if value.is_connected:
                        read_only = True
                    else:
                        value = value.manual_value
            widget.show(value, read_only=read_only or not port_spec["manual_input"])
        else:
            # make some space in case there is no widget
            imgui.dummy(10, 10)
        imgui.end_group()

        # got the area our port takes up now
        # from port_start to port_end (both screen coordinates)
        port_end = imgui.get_item_rect_max()

        # calculate position and size of port connector
        size = imgui.get_item_rect_size()
        x = self.actual_pos[0]
        if not is_input:
            x += self.size[0] + self.padding[0]*2
        y = self.editor.screen_to_local(port_start)[1] + size[1] / 2
        connector_radius = 5.0
        connector_thickness = 2.0
        connector_center = self.editor.local_to_screen((x, y))
        self.port_positions[port_id] = self.editor.screen_to_local(connector_center)

        # find connector bounds for hovering
        # they are a bit bigger than the actual connector
        connector_start, connector_end = None, None
        if is_input:
            connector_start = t_add(port_start, (-30, 0))
            connector_end = port_start[0], port_end[1] + 5
        else:
            connector_start = connector_center[0] - 5, port_start[1]
            connector_end = connector_start[0] + 30, port_end[1]

        # state of port / connector
        is_dragging_connection = self.editor.is_dragging_connection()
        is_connection_droppable = False
        if is_dragging_connection:
            is_connection_droppable = self.editor.is_connection_droppable(self, port_id)
        # whether this port is part of a dragging connection
        is_connection_source = self.editor.is_dragging_connection_source(self, port_id)
        connections = self.connections[port_id]
        # constraint: make sure there is maximum one connection per input
        if is_input:
            assert len(connections) in (0, 1), "but is %d: %s" % (len(connections), connections)

        hovered_port = imgui.is_window_hovered() and t_between(port_start, port_end, io.mouse_pos)
        hovered_connector = imgui.is_window_hovered() and t_between(connector_start, connector_end, io.mouse_pos)
        hovered = hovered_connector or hovered_port

        # decide port bullet color
        bullet_color = get_connection_color(port_spec["dtype"])
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
        deleteable = is_input and len(connections) > 0
        if hovered_connector and deleteable and not is_dragging_connection:
            imgui.set_tooltip("Delete connection")
            if imgui.is_mouse_clicked(0):
                self.editor.remove_connection(connections[0])
                # little tweak: start dragging a new connection once a connection is deleted
                self.editor.drag_connection(self, port_id)
        elif hovered and is_dragging_connection and is_connection_droppable:
            highlight_channel = CHANNEL_NODE_BACKGROUND
            highlight_color = COLOR_PORT_HIGHLIGHT_POSITIVE_ACTIVE
            imgui.set_tooltip("Drop connection")
            if imgui.is_mouse_released(0):
                self.editor.drop_connection(self, port_id)
        elif not is_dragging_connection and hovered_connector:
            imgui.set_tooltip("Create connection")
            if imgui.is_mouse_clicked(0):
                self.editor.drag_connection(self, port_id)

        old_channel = draw_list.channels_current

        draw_list.channels_set_current(CHANNEL_PORT)
        # port connector drawing
        if len(connections) > 0:
            draw_list.add_circle_filled(connector_center, connector_radius, bullet_color, 6)
        else:
            draw_list.add_circle(connector_center, connector_radius, bullet_color, 6, connector_thickness)
        if hovered and not (is_dragging_connection and not is_connection_droppable):
            draw_list.add_circle(connector_center, connector_radius * 2, bullet_color, 6, connector_thickness)

        draw_list.channels_set_current(CHANNEL_PORT_LABEL)
        label = port_spec["name"]
        size = imgui.calc_text_size(label)
        text_pos = None
        if not is_input:
            text_pos = t_add(connector_center, (10, -size[1] / 2))
        else:
            text_pos = t_add(connector_center, (-10 - size[0], -size[1] / 2))
        draw_list.add_text(text_pos, imgui.get_color_u32_rgba(0.7, 0.7, 0.7, 1.0), label)

        draw_list.channels_set_current(highlight_channel)
        # port highlight drawing
        draw_list.add_rect_filled(port_start, port_end, highlight_color)

        draw_list.channels_set_current(old_channel)

        imgui.pop_id()

        #profile.disable()

    def show_ports(self, draw_list, ports):
        io = self.io

        imgui.begin_group()
        for port_id, port_spec in ports.items():
            self.show_port(draw_list, port_id, port_spec)
        imgui.end_group()

    def show(self, draw_list):
        io = self.io

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
                    if node != self:
                        assert not node.dragging, "Only one node may execute drag operation"
                    # pos = old pos + delta
                    node.pos = t_sub(node.dragging_node_start, delta)
                    self.editor.node_ui_state_changed(node)

        # draw background
        upper_left = self.editor.local_to_screen(self.actual_pos)
        lower_right = t_add(upper_left, self.size_with_padding)
        with draw_on_channel(draw_list, CHANNEL_NODE_BACKGROUND):
            draw_list.add_rect_filled(upper_left, lower_right, COLOR_NODE_BACKGROUND, 0.0)

        # draw content of node
        # (set_cursor_pos is window coordinates)
        imgui.set_cursor_pos(self.editor.local_to_window(t_add(self.actual_pos, self.padding)))
        imgui.begin_group()
        if self.spec.options["show_title"]:
            imgui.text(self.spec.name)
        if not self.collapsed:
            if len(self.instance.input_ports):
                imgui.begin_group()
                self.show_ports(draw_list, self.instance.input_ports)
                imgui.end_group()
                imgui.same_line()

            if len(self.instance.output_ports):
                imgui.begin_group()
                self.show_ports(draw_list, self.instance.output_ports)
                imgui.end_group()

            # show custom node ui
            self.instance._show_custom_ui()

        imgui.end_group()

        # all the imgui items inside the node are rendered,
        # we can update the known size of the node
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
                    self.touch_z_index()
                    self.editor.node_ui_state_changed(self)
                elif not self.collapsed and io.mouse_wheel > 0:
                    self.collapsed = True
                    self.touch_z_index()
                    self.editor.node_ui_state_changed(self)
            # handle selection
            if imgui.is_mouse_clicked(0):
                # ctrl modifier toggles selection
                if io.key_ctrl:
                    self.selected = not self.selected
                # otherwise select only this node
                else:
                    if not self.selected:
                        for node in self.editor.nodes:
                            node.selected = False
                        self.touch_z_index()
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
            imgui.separator()
            self.instance._show_custom_context()
            imgui.separator()
            imgui.menu_item("class %s" % str(self.spec.cls), None, False, False)
            imgui.menu_item("node #%d" % self.window_id, None, False, False)
            imgui.end_popup()

        # handle clicking the node once it's selected as dragging
        if self.hovered and imgui.is_mouse_clicked(0) and not io.key_ctrl \
                and self.selected and not self.editor.is_dragging_connection():
            # mark this node as being dragged
            self.dragging = True
            self.dragging_mouse_start = io.mouse_pos
            # set for all selected nodes where they were at beginning of dragging
            for node in self.editor.nodes:
                if node.selected:
                    node.dragging_node_start = node.actual_pos
        # stop dragging once mouse is released again
        if self.dragging and imgui.is_mouse_released(0):
            self.dragging = False
            self.dragging_mouse_start = None
            for node in self.editor.nodes:
                node.dragging_node_start = None

        # draw border(s)
        with draw_on_channel(draw_list, CHANNEL_NODE_BACKGROUND):
            draw_list.add_rect(upper_left, lower_right, COLOR_NODE_BORDER, 0.0)
            if self.hovered:
                draw_list.add_rect(upper_left_hover, lower_right_hover, COLOR_NODE_BORDER_HOVERED, 0.0)
            if self.selected:
                draw_list.add_rect(upper_left_selection, lower_right_selection, COLOR_NODE_BORDER_SELECTED, 0.0)

        imgui.pop_id()
        imgui.set_cursor_pos(old_cursor_pos)

class NodeEditor:
    def __init__(self, node_specs):
        # available nodes for this editor
        self.node_specs = node_specs

        self.graph = NodeGraph()
        self.graph.listeners.append(self)

        self.ui_nodes = {}

        # collection of ui nodes/connections
        #self.nodes = []
        self.nodes_z_index = 0
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
        self.context_search_test = ""

        # performance measurement stuffs
        self.fps = 0.0
        self.editor_time = 0.0
        self.editor_time_relative = 0.0
        self.processing_time = 0.0
        self.processing_time_relative = 0.0
        self.show_test_window = False

        self.io = imgui.get_io()
        self.key_map = list(self.io.key_map)

        if os.path.isfile("session.json"):
            self.graph.load("session.json")

    @property
    def nodes(self):
        return self.ui_nodes.values()

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
    # node graph handlers
    #

    def created_node(self, node, ui_data):
        #print("created node")
        n = Node(self, node, ui_data)
        self.ui_nodes[node.id] = n

    def removed_node(self, node):
        #print("removed node")
        assert node.id in self.ui_nodes
        n = self.ui_nodes[node.id]
        del self.ui_nodes[node.id]

    def created_connection(self, src_node, src_port_id, dst_node, dst_port_id):
        #print("created connection")
        src_node = self.ui_nodes[src_node.id]
        dst_node = self.ui_nodes[dst_node.id]
        self.connections.append(Connection(self, src_node, src_port_id, dst_node, dst_port_id))

    def removed_connection(self, src_node, src_port_id, dst_node, dst_port_id):
        #print("removed connection")

        src_node = self.ui_nodes[src_node.id]
        dst_node = self.ui_nodes[dst_node.id]

        for c in self.connections:
            if (c.src_node, c.src_port_id, c.dst_node, c.dst_port_id) \
                != (src_node, src_port_id, dst_node, dst_port_id):
                continue
            c.disconnect()
            self.connections.remove(c)
            return
        assert False, "No ui connection found to remove"

    # not called by graph, but by ui nodes
    def node_ui_state_changed(self, node):
        ui_data = {}
        ui_data["pos"] = node.pos
        ui_data["collapsed"] = node.collapsed
        self.graph.set_node_ui_data(node.instance, ui_data)

    #
    # editor api functions used by nodes, connections and editor itself
    #

    def touch_z_index(self):
        i = self.nodes_z_index
        self.nodes_z_index += 1
        return i

    def remove_node(self, node):
        #print("editor: remove node")
        self.graph.remove_node(node.instance)

    def remove_connection(self, connection):
        #print("editor: remove connection")
        c = connection
        self.graph.remove_connection(c.src_node.instance, c.src_port_id, c.dst_node.instance, c.dst_port_id)

    def drag_connection(self, node, port_id):
        assert self.dragging_connection is None
        #print("Start dragging connection")
        self.dragging_connection = Connection.create(self, node, port_id)
        self.dragging_target_port_type = not node_meta.is_input(port_id)

    def is_dragging_connection(self):
        return self.dragging_connection is not None

    def is_dragging_connection_source(self, node, port_id):
        if not self.is_dragging_connection():
            return False
        return self.dragging_connection.is_end(node, port_id)

    def is_connection_droppable(self, node, port_id):
        assert self.is_dragging_connection()
        # constraint: connect only input with output and vice versa
        if node_meta.is_input(port_id) != self.dragging_target_port_type:
            return False
        # constraint: only one connection per input
        if node_meta.is_input(port_id) and len(node.connections[port_id]) != 0:
            return False
        
        port_spec = node.instance.ports[port_id]
        connection = self.dragging_connection
        other_port_spec = None
        if node_meta.is_input(port_id):
            other_port_spec = connection.src_node.instance.ports[connection.src_port_id]
        else:
            other_port_spec = connection.dst_node.instance.ports[connection.dst_port_id]
        return port_spec["dtype"].base_type == other_port_spec["dtype"].base_type

    def drop_connection(self, node, port_id):
        assert self.is_dragging_connection()
        assert self.is_connection_droppable(node, port_id)

        # connect ui nodes
        connection = self.dragging_connection
        connection.disconnect()
        if node_meta.is_input(port_id):
            connection.dst_node = node
            connection.dst_port_id = port_id
        else:
            connection.src_node = node
            connection.src_port_id = port_id
        self.dragging_connection = None

        c = connection
        self.graph.create_connection(c.src_node.instance, c.src_port_id, c.dst_node.instance, c.dst_port_id)

    #
    # misc stuff
    #

    def timing_callback(self, editor_time, processing_time):
        self.fps = app.clock.get_default().get_fps()
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

    def show_context_menu(self):
        io = self.io
        key_map = self.key_map
        key_g = glfw.GLFW_KEY_G
        key_up_arrow = key_map[imgui.KEY_UP_ARROW]
        key_down_arrow = key_map[imgui.KEY_DOWN_ARROW]
        key_escape = key_map[imgui.KEY_ESCAPE]
        is_key_down = lambda key: io.is_key_down(key) and io.get_key_down_duration(key) == 0.0

        just_opened_popup = False
        reopen_popup = False

        # context menu
        no_node_hovered = lambda: not any(map(lambda n: n.hovered, self.nodes))
        if imgui.is_window_hovered() \
                and (imgui.is_mouse_clicked(1) or is_key_down(key_g)) \
                and no_node_hovered():
            # remember where context menu was opened
            # (to place node there)
            self.context_mouse_pos = io.mouse_pos
            imgui.open_popup("context")
            self.context_search_text = ""
            self.context_index = 0
            just_opened_popup = True

        if imgui.begin_popup("context"):
            assert self.context_mouse_pos is not None
            # handle when user right-clicked outside of the popup
            # this should close the popup and re-open it at the new position
            # re-opening must be handled outside of begin_popup()/end_popup()
            if not just_opened_popup and not imgui.is_window_hovered() and imgui.is_mouse_clicked(1):
                reopen_popup = True

            # set keyboard focus only once
            if not imgui.is_any_item_active():
                imgui.set_keyboard_focus_here()
            imgui.push_item_width(200)
            changed, self.context_search_text = imgui.input_text("", self.context_search_text, 255, imgui.INPUT_TEXT_ENTER_RETURNS_TRUE)

            def filter_nodes(text):
                for i, spec in enumerate(self.node_specs):
                    label = spec.name
                    if spec.options["category"]:
                        label += " (%s)" % spec.options["category"]
                    if not is_substring_partly(text.lower(), label.lower()):
                        continue
                    yield label, spec
            entries = list(filter_nodes(self.context_search_text))

            if is_key_down(key_up_arrow):
                self.context_index -= 1
            if is_key_down(key_down_arrow):
                self.context_index += 1
            if is_key_down(key_escape):
                imgui.close_current_popup()

            self.context_index = max(0, min(len(entries) - 1, self.context_index))
            selected = self.context_index
            imgui.listbox_header("", 200, 200)
            for i, (label, spec) in enumerate(entries):
                imgui.push_id(i)
                is_selected = selected == 0
                imgui.selectable(label, is_selected)
                if imgui.is_item_clicked() or (is_selected and changed):
                    pos = self.screen_to_local(self.context_mouse_pos)
                    #self.nodes.append(Node(self, spec, pos=pos))
                    self.graph.create_node(spec, {"pos" : pos})
                    # TODO it would be nice to set the mouse position back to where the node is now
                    imgui.close_current_popup()
                imgui.pop_id()
                selected -= 1
            if len(entries) == 0:
                imgui.text("Nothing found.")
            imgui.listbox_footer()
            imgui.separator()
            clicked, self.show_test_window = imgui.menu_item("show demo window", None, self.show_test_window)
            if clicked:
                imgui.set_window_focus("ImGui Demo")
            if imgui.menu_item("reset offset")[0]:
                self.offset = (0, 0)

            imgui.end_popup()

        if reopen_popup:
            imgui.close_current_popup()
            imgui.open_popup("context")

        #profile.disable()

    def show(self):
        # create editor window
        #profile.enable()

        io = imgui.get_io()
        w, h = io.display_size
        imgui.set_next_window_position(0, 0)
        imgui.set_next_window_size(w, h)

        flags = imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_BRING_TO_FRONT_ON_FOCUS | imgui.WINDOW_NO_SCROLLBAR | imgui.WINDOW_NO_SCROLL_WITH_MOUSE
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
        # little hack: to get overlapping nodes and such correct,
        #    render nodes in an order. nodes request a new z-index from the
        #    editor when they got touched and should be in the foreground again
        for node in sorted(self.nodes, key=lambda n: n.z_index):
            # simple culling
            node_start = self.local_to_screen(node.actual_pos)
            node_end = t_add(node_start, node.size_with_padding)
            if t_cull(node_start, node_end):
                continue

            with draw_on_channel(draw_list, CHANNEL_NODE):
                node.show(draw_list)
            # TODO
            # unfortunately we have to merge and split the draw list multiple times for that
            # maybe there is a better way
            draw_list.channels_merge()
            draw_list.channels_split(CHANNEL_COUNT)
            draw_list.channels_set_current(CHANNEL_DEFAULT)
        for connection in self.connections:
            connection.show(draw_list)
        if self.dragging_connection is not None:
            self.dragging_connection.show(draw_list)

        # dropping connection to ports is handled by nodes
        # we're checking here if a connection was dropped into nowhere
        if self.is_dragging_connection() and imgui.is_mouse_released(0):
            self.dragging_connection.disconnect()
            #self.connections.remove(self.dragging_connection)
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
            key_map = self.key_map
            key_a = key_map[imgui.KEY_A]
            key_d = glfw.GLFW_KEY_D
            key_i = glfw.GLFW_KEY_I
            key_escape = key_map[imgui.KEY_ESCAPE]
            key_delete = key_map[imgui.KEY_DELETE]
            is_key_down = lambda key: io.is_key_down(key) and io.get_key_down_duration(key) == 0.0
            if is_key_down(key_a):
                for node in list(self.nodes):
                    node.selected = True
            if is_key_down(key_i):
                for node in list(self.nodes):
                    node.selected = not node.selected
            if is_key_down(key_escape):
                for node in list(self.nodes):
                    node.selected = False
            if is_key_down(key_delete) or is_key_down(key_d):
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

        if imgui.button("Clear"):
            self.graph.clear()

        imgui.same_line()
        if imgui.button("Save"):
            imgui.open_popup("save")
        save_path = node_widget.imgui_pick_file("save", assets.SAVE_PATH)
        if save_path is not None:
            f = open(save_path, "w")
            f.write(self.graph.serialize())
            f.close()

        imgui.same_line()
        if imgui.button("Load"):
            imgui.open_popup("load")
        load_path = node_widget.imgui_pick_file("load", assets.SAVE_PATH)
        if load_path is not None:
            self.graph.load(load_path, append=False)
        
        imgui.same_line()
        if imgui.button("Import"):
            imgui.open_popup("import")
        import_path = node_widget.imgui_pick_file("import", assets.SAVE_PATH)
        if import_path is not None:
            self.graph.load(import_path, append=True)

        imgui.same_line()
        imgui.text("fps: %.2f" % self.fps)
        imgui.text("editor time: %.2f ms ~ %.2f%%" % (self.editor_time * 1000.0, self.editor_time_relative * 100.0))
        imgui.text("processing time: %.2f ms ~ %.2f%%" % (self.processing_time * 1000.0, self.processing_time_relative * 100.0))

        # gather "graph" of node instances
        #imgui.text("")
        #instances, circular = self.node_instances_sorted
        #num_nodes = len(instances)
        #num_connections = sum([ sum([ 1 if v.is_connected else 0 for v in node.inputs.values() ]) for node in instances ])
        #assert num_connections == len(self.connections)
        #imgui.text("#%d nodes, #%d connections" % (num_nodes, num_connections))
        #imgui.text("Sorted instances:")
        #imgui.same_line()

        # evaluate nodes
        # TODO move this out or so
        #processing_time = 0.0
        #if circular:
        #    # TODO show a warning maybe
        #    pass
        #else:
        #    imgui.text(" -> ".join([ instance.spec.name for instance in instances ]))
        #
        #    start = time.time()
        #    active_instances = set()
        #    for instance in instances:
        #        if instance.process():
        #            active_instances.add(instance)
        #    for instance in instances:
        #        instance.evaluated = False
        #    end = time.time()
        #    processing_time = end - start
        #
        #    imgui.text("Active instances: %d: %s" % (len(active_instances), [ instance.spec.name for instance in active_instances]))

        # finish our drawing
        draw_list.channels_merge()

        # show context
        self.show_context_menu()

        if self.show_test_window:
            imgui.show_test_window()
        imgui.end()

        #profile.disable()

# sort by node categories and then by names
node_types = node_meta.Node.get_sub_nodes(include_self=False)
node_types.sort(key=lambda n: n.spec.name)
node_types.sort(key=lambda n: n.spec.options["category"])

# TODO think about naming
#   ui nodes vs. node instances vs. node types
node_specs = [ n.spec for n in node_types ]
node_specs = list(filter(lambda s: not s.options["virtual"], node_specs))
editor = NodeEditor(node_specs)

editor_time = 0.0
processing_time = 0.0
time_count = 0

@window.event
def on_draw(event):
    global editor_time, processing_time, time_count

    # evaluate nodes
    start = time.time()
    editor.graph.evaluate()
    processing_time += time.time() - start

    # render editor
    gl.glClear(gl.GL_COLOR_BUFFER_BIT)

    start = time.time()
    imgui_renderer.process_inputs()
    imgui.new_frame()

    editor.show()

    imgui.render()
    draw = imgui.get_draw_data()
    imgui_renderer.render(draw)

    editor_time += time.time() - start

    # performance stats
    time_count += 1
    if time_count >= 30:
        editor.timing_callback(editor_time / time_count, processing_time / time_count)
        editor_time = 0.0
        processing_time = 0.0
        time_count = 0

@window.event
def on_key_press(key, modifier):
    print("Glumpy: Pressed key: %s" % key)
    if key == ord("Q"):
        editor.graph.stop()
        editor.graph.save("session.json")
        profile.dump_stats("profile.stats")
        sys.exit(0)

if __name__ == "__main__":
    window.show()
    app.run()
