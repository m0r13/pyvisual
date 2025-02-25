#!/usr/bin/env python3

# TODO write a setup.py with cython stuff!
import pyximport; pyximport.install()

import OpenGL
#OpenGL.ERROR_CHECKING = False
#OpenGL.ERROR_ON_COPY = True

import cProfile
import contextlib
import glob
import json
import numpy as np
import os
import random
import sys
import time
import traceback
from collections import defaultdict

import imgui
import pyvisual.node as node_meta
import pyvisual.node.dtype as node_dtype
# import this later than all node types (widget is required by pyvisual.node.io.system_var)
import pyvisual.editor.widget as node_widget

from glumpy import app, gloo, gl, glm
from glumpy.ext import glfw
from pyvisual import assets, util
from pyvisual.editor import glumpy_imgui
from pyvisual.editor.graph import RootGraph, NodeGraph, NodeGraphListener
from pyvisual.editor.graph_traits import GraphTraits
from pyvisual.node.io.texture import Renderer
from pyvisual.node.op.gpu.base import ShaderNodeLoader
from pyvisual.node.value import ConnectedValue
from pyvisual.node.io import system_var

profile = cProfile.Profile()

# create window / opengl context already here
# imgui seems to cause problems otherwise with imgui.get_color_u32_rgba without context
external_window = app.Window(title="pyvisual optics external", color=(0, 0, 0, 1))
window = app.Window(context=external_window, title="pyvisual optics", color=(0, 0, 0, 1))
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

def match_substring_partly(substring, string):
    # returns (True, n) if substring is a substring of string,
    # n determines how many characters are skipped in total
    # where characters in string can be skipped
    # otherwise it returns (False, _)
    # example: "infloat" is in "inputfloat"

    # empty substring always contained
    if not substring:
        return True, 0
    # index in substring
    j = 0
    # number of skipped characters
    n = 0
    # last index in string where we found the same character
    last_match = None
    for i, c in enumerate(string):
        if c == substring[j]:
            # advance one character in substring
            j += 1
            if last_match is not None:
                n += i - last_match - 1
            last_match = i
            if j == len(substring):
                return True, n
    return j == len(substring), n

def multiply_alpha(color, alpha):
    # TODO use this instead of lambdas below?
    pass

COLOR_EDITOR_BACKGROUND = lambda alpha: imgui.get_color_u32_rgba(0.1, 0.1, 0.1, alpha)
COLOR_EDITOR_GRID = lambda alpha: imgui.get_color_u32_rgba(0.3, 0.3, 0.3, alpha)
COLOR_NODE_BACKGROUND = lambda alpha: imgui.get_color_u32_rgba(0.0, 0.0, 0.0, alpha)
COLOR_NODE_ACTIVE_INDICATOR = imgui.get_color_u32_rgba(0.0, 0.5, 0.0, 0.5)
COLOR_NODE_BORDER = imgui.get_color_u32_rgba(0.7, 0.7, 0.7, 1.0)
COLOR_NODE_BORDER_HOVERED = imgui.get_color_u32_rgba(1.0, 1.0, 1.0, 0.5)
COLOR_NODE_BORDER_SELECTED = imgui.get_color_u32_rgba(1.0 * 0.75, 0.697 * 0.75, 0.0, 0.8)

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
    node_dtype.base_vec2 : _red,
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
CHANNEL_CONNECTION1 = 5
CHANNEL_CONNECTION2 = 6
CHANNEL_PORT = 2
CHANNEL_PORT_LABEL = 7
CHANNEL_SELECTION = 8
CHANNEL_COUNT = 9

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

class UIConnection:
    def __init__(self, ui_graph, src_node, src_port_id, dst_node, dst_port_id):
        self.ui_graph = ui_graph
        self.src_node = src_node
        self.src_port_id = src_port_id
        self.dst_node = dst_node
        self.dst_port_id = dst_port_id
        # is set by connect()
        self.dtype = None
        self.color = 0
        self.connect()

        self.p0 = None
        self.p1 = None
        self.visible = None

    @property
    def mouse_node(self):
        if isinstance(self.src_node, MouseDummyNode):
            return self.src_node
        elif isinstance(self.dst_node, MouseDummyNode):
            return self.dst_node
        assert False

    def connect(self):
        self.src_node.attach_connection(self.src_port_id, self)
        self.dst_node.attach_connection(self.dst_port_id, self)

        self.dtype = None
        if self.src_port_id is not None:
            self.dtype = self.src_node.instance.ports[self.src_port_id]["dtype"]
        elif self.dst_port_id is not None:
            self.dtype = self.dst_node.instance.ports[self.dst_port_id]["dtype"]
        else:
            assert False
        self.color = get_connection_color(self.dtype)

    def disconnect(self):
        self.src_node.detach_connection(self.src_port_id, self)
        self.dst_node.detach_connection(self.dst_port_id, self)

        self.dtype = None
        self.color = 0

    def update_position(self):
        self.p0 = self.src_node.get_port_position(self.src_port_id)
        self.p1 = self.dst_node.get_port_position(self.dst_port_id)

    def reset_position(self):
        self.p0 = None
        self.p1 = None
        self.visible = None

    def is_visible(self):
        if self.visible is None:
            if self.p0 is None:
                self.update_position()

            (x0, y0), (x1, y1) = self.p0, self.p1
            start = min(x0, x1), min(y0, y1)
            end = max(x0, x1), max(y0, y1)
            self.visible = not t_cull(start, end)
        return self.visible

    def show(self, draw_list):
        # is connected when both sides are on a node
        connected = not isinstance(self.src_node, MouseDummyNode) \
                and not isinstance(self.dst_node, MouseDummyNode)
        dragging_connection = self.ui_graph.is_dragging_connection()

        color = None
        if dragging_connection and connected:
            # show connections while other connection is dragged as inactive
            color = COLOR_PORT_BULLET_DISABLED
        elif dragging_connection and not connected:
            # show connection that is being dragged as active
            color = COLOR_PORT_BULLET_HOVERED
        else:
            color = self.color

        # TODO this is a bit flawed currently
        # remove itself when input/output port doesn't exist
        # (in case one was a custom port and got removed by the node itself)
        # actually the nodes should somehow trigger the connection removal itself
        if (isinstance(self.src_node, UINode) and not self.src_port_id in self.src_node.instance.ports) \
                or (isinstance(self.dst_node, UINode) and not self.dst_port_id in self.dst_node.instance.ports):
            self.ui_graph.remove_connection(self)
            return

        if self.p0 is None:
            self.update_position()
        p0 = self.p0
        p1 = self.p1

        delta = p1[0] - p0[0], p1[1] - p0[1]
        offset_x = min(200, abs(delta[0])) * 0.5
        offset_y = 0
        if delta[0] < 0:
            offset_x = min(200, 0.5 * abs(delta[0]))
            offset_y = min(100, abs(delta[1]))
        if p0[1] > p1[1]:
            offset_y *= -1.0
        b0 = t_add(p0, (offset_x, offset_y))
        b1 = t_add(p1, (-offset_x, -offset_y))

        # remember old draw channel
        channel = draw_list.channels_current

        # draw background of connection
        draw_list.channels_set_current(CHANNEL_CONNECTION1)
        draw_list.add_bezier_curve(p0, b0, b1, p1, imgui.get_color_u32_rgba(0.2, 0.2, 0.2, 0.5), 10.0)

        # draw actual connection
        draw_list.channels_set_current(CHANNEL_CONNECTION2)
        # simple lines
        #draw_list.add_line(p0, p1, color, 2.0)
        # fancy bezier
        draw_list.add_bezier_curve(p0, b0, b1, p1, color, 2.0)
        # to visualize the control points
        #draw_list.add_circle_filled(b0, 3, imgui.get_color_u32_rgba(0.0, 1.0, 0.0, 1.0))
        #draw_list.add_circle_filled(b1, 3, imgui.get_color_u32_rgba(0.0, 0.0, 1.0, 1.0))

        draw_list.channels_set_current(channel)

    def is_end(self, node, port_id):
        return (self.src_node == node and self.src_port_id == port_id) \
                or (self.dst_node == node and self.dst_port_id == port_id)

    @staticmethod
    def create(editor, node, port_id):
        if node_meta.is_input(port_id):
            return UIConnection(editor, dst_node=node, dst_port_id=port_id,
                    src_node=MouseDummyNode(), src_port_id=None)
        else:
            return UIConnection(editor, src_node=node, src_port_id=port_id,
                    dst_node=MouseDummyNode(), dst_port_id=None)

class MouseDummyNode:
    def __init__(self):
        self._position = None

    def keep_position(self):
        self._position = self.get_port_position(None)

    def attach_connection(self, *args):
        pass
    def detach_connection(self, *args):
        pass

    def get_port_position(self, port_id):
        if self._position is None:
            return imgui.get_io().mouse_pos
        return self._position

class UINode:
    
    id_counter = 0

    def __init__(self, ui_graph, instance, ui_data):
        self.ui_graph = ui_graph
        self.instance = instance
        self.spec = instance.spec

        # id for imgui-rendered node
        self.window_id = UINode.id_counter
        UINode.id_counter += 1
        self.z_index = 0
        self.touch_z_index()

        self.port_positions = {}
        self.widgets = {}
        self.widget_port_specs = {}
        self.ui_connections = defaultdict(lambda: [])

        #
        # size information of node (everything in local position)
        #
        self.padding = 5, 5
        self.pos = ui_data.get("pos", (0, 0))
        # self.actual_pos
        self.size = 10, 10

        # things cached
        self.visible = None

        #
        # state of node
        #
        self.collapsed = ui_data.get("collapsed", False)
        self.selected = ui_data.get("selected", False)

        # is this node being dragged?
        # note: - for dragging selections of nodes, only the handle (clicked) node is marked as dragging
        #       - all others get dragging_from set
        self.dragging = False
        # if this node is the handle: where was mouse at beginning of drag operation (screen pos)
        self.dragging_mouse_start = None
        # where was this node at the beginning of drag operation? (local pos)
        self.dragging_node_start = None
        self.hovered = False

        # information that the node's position should be set so that a specific port is at a specific position
        self._align_port_id = None
        self._align_port_pos = None
        # set to 1 then because ui node needs one frame to calculate correct size
        self._align_port_counter = 0

        # TODO this is not so nice, have all ui data attributes with setters and call this automatically
        # trigger update of ui data
        self.ui_graph.update_node_ui_state(self)

        self.io = imgui.get_io()

    @property
    def pos(self):
        return self._pos
    @pos.setter
    def pos(self, pos):
        self._pos = pos

        # local pos with node grid applied
        if EDITOR_NODE_GRID_SIZE > 1.0:
            self.actual_pos = round_next(self.pos[0], EDITOR_NODE_GRID_SIZE), round_next(self.pos[1], EDITOR_NODE_GRID_SIZE)
        else:
            self.actual_pos = self.pos

    @property
    def size_with_padding(self):
        return t_add(self.size, t_mul(self.padding, 2))

    def reset_position(self):
        self.visible = None

    def is_visible(self):
        if self.visible is None:
            size = self.size_with_padding
            start = self.ui_graph.local_to_screen(self.actual_pos)
            end = start[0]+size[0], start[1]+size[1]
            self.visible = not t_cull(start, end)
        return self.visible

    # set the nodes position (as soon as size and position of port is known)
    # such that the specific port is at a specific position
    def align_port_at(self, port_id, pos):
        self._align_port_id = port_id
        self._align_port_pos = pos
        # see where _align_port_counter is also used
        self._align_port_counter = 1

    def touch_z_index(self):
        self.z_index = self.ui_graph.touch_z_index()

    def attach_connection(self, port_id, connection):
        self.ui_connections[port_id].append(connection)

    def detach_connection(self, port_id, connection):
        self.ui_connections[port_id].remove(connection)

    def get_widget(self, port_id):
        # TODO performance? also editor could handle this better maybe
        if port_id in self.widget_port_specs:
            port_spec = self.instance.ports[port_id]
            old_port_spec = self.widget_port_specs[port_id]
            # compare only dtype for now
            if old_port_spec["dtype"] != port_spec["dtype"]:
                del self.widgets[port_id]

        if not port_id in self.widgets:
            assert port_id in self.instance.ports, "Port %s must be in instance ports" % port_id
            port_spec = self.instance.ports[port_id]
            dtype = port_spec["dtype"]
            dtype_args = port_spec["dtype_args"]
            self.widgets[port_id] = node_widget.create_widget(dtype, dtype_args, self)
            self.widget_port_specs[port_id] = dict(port_spec)
        return self.widgets[port_id]

    def get_port_position(self, port_id):
        assert port_id in self.instance.ports, "Port %s must be in instance ports" % port_id

        # handle collapsed node
        if self.collapsed or port_id not in self.port_positions:
            pos = self.actual_pos
            x = pos[0] if node_meta.is_input(port_id) else pos[0]+self.size[0]+self.padding[0]*2
            y = pos[1] + (self.size[1] + self.padding[1] * 2) / 2
            return self.ui_graph.local_to_screen((x, y))
        return self.ui_graph.local_to_screen(self.port_positions[port_id])

    def show_port(self, draw_list, interaction_allowed, port_id, port_spec):
        #profile.enable()

        io = self.io

        if port_spec["hide"]:
            return
        if port_spec["dummy"]:
            # 6 == frame padding * 2
            imgui.dummy(1, imgui.get_text_line_height() + 6)
            return
        name = port_spec["name"]
        dtype = port_spec["dtype"]
        is_input = node_meta.is_input(port_id)

        # ui
        imgui.push_id(port_id)
        imgui.begin_group()

        # screen coordinates here
        # extra padding is additional padding that is added to port hover areas
        extra_padding = 2
        port_start = imgui.get_cursor_screen_pos()
        port_start = (port_start[0] - extra_padding, port_start[1] - extra_padding)

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
                if isinstance(value, ConnectedValue):
                    if value.is_connected():
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
        port_end = (port_end[0] + extra_padding, port_end[1] + extra_padding)

        # calculate position and size of port connector
        size = imgui.get_item_rect_size()
        x = self.actual_pos[0]
        if not is_input:
            x += self.size[0] + self.padding[0]*2
        y = self.ui_graph.screen_to_local(port_start)[1] + size[1] / 2
        connector_radius = 5.0
        connector_thickness = 2.0
        connector_center = self.ui_graph.local_to_screen((x, y))
        # port position is in local coordinates
        self.port_positions[port_id] = (x, y)

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
        is_dragging_connection = self.ui_graph.is_dragging_connection()
        is_connection_droppable = False
        if is_dragging_connection:
            is_connection_droppable = self.ui_graph.is_connection_droppable(self, port_id)
        # whether this port is part of a dragging connection
        is_connection_source = self.ui_graph.is_dragging_connection_source(self, port_id)
        connections = self.ui_connections[port_id]
        # constraint: make sure there is maximum one connection per input
        if is_input:
            # but actually there can be two connections on an input
            # when a new connection is dragged in place
            assert len(connections) <= 2, "but is %d: %s" % (len(connections), connections)

        hoverable = imgui.is_window_hovered() and interaction_allowed
        hovered_port = hoverable and t_between(port_start, port_end, io.mouse_pos)
        hovered_connector = hoverable and t_between(connector_start, connector_end, io.mouse_pos)
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
                ### self.ui_graph.remove_connection(connections[0])
                # little tweak: start dragging a new connection once a connection is deleted
                self.ui_graph.drag_connection(self, port_id, remove_connection=connections[0])
        elif hovered and is_dragging_connection and is_connection_droppable:
            highlight_channel = CHANNEL_NODE_BACKGROUND
            highlight_color = COLOR_PORT_HIGHLIGHT_POSITIVE_ACTIVE
            imgui.set_tooltip("Drop connection")
            if imgui.is_mouse_released(0):
                self.ui_graph.finish_dragging_connection(self, port_id)
        elif not is_dragging_connection and hovered_connector:
            imgui.set_tooltip("Create connection")
            if imgui.is_mouse_clicked(0):
                self.ui_graph.drag_connection(self, port_id)

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

        padding = (2, 2)
        size_with_padding = size[0] + 2*padding[0], size[1] + 2*padding[1]
        alpha = self.ui_graph.ui_graph_data.node_bg_alpha
        draw_list.add_rect_filled(t_sub(text_pos, padding), t_add(text_pos, size_with_padding), COLOR_NODE_BACKGROUND(alpha * 0.5))
        draw_list.add_text(text_pos, imgui.get_color_u32_rgba(0.8, 0.8, 0.8, 1.0), label)

        draw_list.channels_set_current(highlight_channel)
        # port highlight drawing
        draw_list.add_rect_filled(port_start, port_end, highlight_color)

        draw_list.channels_set_current(old_channel)

        imgui.pop_id()

        #profile.disable()

    def show_ports(self, draw_list, interaction_allowed, ports):
        io = self.io
        interacted = False

        imgui.begin_group()
        for port_id, port_spec in ports:
            if self.show_port(draw_list, interaction_allowed, port_id, port_spec):
                interacted = True
        imgui.end_group()

        return interacted

    def show_context_ports(self, ports):
        for i, (port_id, port_spec) in enumerate(ports):
            widget = self.get_widget(port_id)
            if widget is None:
                continue
            imgui.push_id(i)

            # determine value associated with this port
            value = self.instance.get_value(port_id)
            # and whether we can change it
            read_only = False
            if node_meta.is_input(port_id):
                # we can change value of input port only if nothing is connected
                # otherwise it's a read-only widget that just shows the value for the user
                if isinstance(value, ConnectedValue):
                    if value.is_connected():
                        read_only = True
                    else:
                        value = value.manual_value

            text_start = imgui.get_cursor_screen_pos()
            imgui.text(port_spec["name"])

            imgui.set_cursor_screen_pos((text_start[0] + 150, text_start[1]))
            widget.show(value, read_only=read_only or not port_spec["manual_input"])

            imgui.pop_id()

    def show(self, draw_list, interaction_allowed):
        io = self.io
        interacted = False

        imgui.push_id(self.window_id)
        old_cursor_pos = imgui.get_cursor_pos()

        actual_pos = self.actual_pos

        # calculate position of drag operation first
        # TODO: this causes a frame delay for nodes that are rendered before this
        # maybe it's fixable without too much effort
        if self.dragging:
            assert self.selected
            assert self.dragging_mouse_start is not None
            delta = t_sub(self.dragging_mouse_start, io.mouse_pos)
            for node in self.ui_graph.nodes:
                if node.selected:
                    if node != self:
                        assert not node.dragging, "Only one node may execute drag operation"
                    # pos = old pos + delta
                    node.pos = t_sub(node.dragging_node_start, delta)
                    self.ui_graph.update_node_ui_state(node)

        # draw background
        upper_left = self.ui_graph.local_to_screen(actual_pos)
        lower_right = t_add(upper_left, self.size_with_padding)
        with draw_on_channel(draw_list, CHANNEL_NODE_BACKGROUND):
            if self.instance._last_evaluated > time.time() - 0.2:
                size = imgui.get_text_line_height()
                offset = 4
                a = lower_right[0] - size + offset, upper_left[1] - offset
                b = lower_right[0] + offset, upper_left[1] + size - offset
                draw_list.add_rect_filled(a, b, COLOR_NODE_ACTIVE_INDICATOR)
                #draw_list.add_rect(a, b, COLOR_NODE_BORDER, 0.0)
            alpha = self.ui_graph.ui_graph_data.node_bg_alpha
            draw_list.add_rect_filled(upper_left, lower_right, COLOR_NODE_BACKGROUND(alpha), 0.0)

        # draw content of node
        # (set_cursor_pos is window coordinates)
        imgui.set_cursor_pos(self.ui_graph.local_to_window(t_add(actual_pos, self.padding)))
        imgui.begin_group()
        if self.spec.options["show_title"]:
            imgui.text(self.instance.node_title)
            #imgui.text(self.spec.name + " (%d)" % self.instance.dfs_index)
        elif self.collapsed:
            imgui.text(self.instance.collapsed_node_title)
            #imgui.text(self.instance.collapsed_node_title + " (%d)" % self.instance.dfs_index)
        if not self.collapsed:
            port_filter = lambda port: not port[1]["hide"] and port[1]["group"] == "default"
            inputs = list(filter(port_filter, self.instance.input_ports.items()))
            outputs = list(filter(port_filter, self.instance.output_ports.items()))

            if len(inputs):
                imgui.begin_group()
                if self.show_ports(draw_list, interaction_allowed, inputs):
                    interacted = True
                imgui.end_group()
                # TODO hacked layout
                if len(outputs) or self.spec.name in ("Plot", "BeatMonitor"):
                    imgui.same_line()

            if len(outputs):
                imgui.begin_group()
                if self.show_ports(draw_list, interaction_allowed, outputs):
                    interacted = True
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
        padding_selection = (4, 4)
        upper_left = self.ui_graph.local_to_screen(actual_pos)
        upper_left_hover = t_sub(upper_left, padding_hover)
        upper_left_selection = t_sub(upper_left, padding_selection)
        lower_right = t_add(upper_left, self.size_with_padding)
        lower_right_hover = t_add(lower_right, padding_hover)
        lower_right_selection = t_add(lower_right, padding_selection)

        hoverable = interaction_allowed and imgui.is_window_hovered()
        self.hovered = hoverable and t_between(upper_left_selection, lower_right_selection, io.mouse_pos)

        # handle clicks / scrolling on the node
        if not self.ui_graph.is_dragging_connection() and self.hovered and not imgui.is_any_item_active():
            # handle collapsing/expanding
            collapsed_title = self.instance.collapsed_node_title
            collapsible = self.spec.options["show_title"] or collapsed_title is not None
            if collapsible:
                if self.collapsed and io.mouse_wheel < 0:
                    self.collapsed = False
                    self.touch_z_index()
                    self.ui_graph.update_node_ui_state(self)
                elif not self.collapsed and io.mouse_wheel > 0:
                    self.collapsed = True
                    self.touch_z_index()
                    self.ui_graph.update_node_ui_state(self)
            # handle selection
            if imgui.is_mouse_clicked(0) and not io.key_shift:
                # ctrl modifier toggles selection
                if io.key_ctrl:
                    self.selected = not self.selected
                    self.ui_graph.update_node_ui_state(self)
                # otherwise select only this node
                else:
                    if not self.selected:
                        for node in self.ui_graph.nodes:
                            node.selected = False
                            self.ui_graph.update_node_ui_state(node)
                        self.touch_z_index()
                    self.selected = True
                    self.ui_graph.update_node_ui_state(self)
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
                self.ui_graph.remove_node(self)
            if imgui.menu_item("expand..." if self.collapsed else "collaps...")[0]:
                self.collapsed = not self.collapsed
            if self.instance.HAS_SUBGRAPH and imgui.menu_item("open subgraph")[0]:
                name = self.instance.node_title
                graph = self.instance.subgraph
                parent_graph = self.ui_graph.graph
                self.ui_graph.subgraph_handler.open_subgraph(name, graph, parent_graph)
            imgui.separator()

            additional_filter = lambda port: not port[1]["hide"] and port[1]["group"] == "additional"
            inputs = list(filter(additional_filter, self.instance.input_ports.items()))
            outputs = list(filter(additional_filter, self.instance.output_ports.items()))

            if len(inputs) > 0:
                imgui.text("additional inputs")
                self.show_context_ports(inputs)
                imgui.separator()
            if len(outputs) > 0:
                imgui.text("additional outputs")
                self.show_context_ports(outputs)
                imgui.separator()

            self.instance._show_custom_context()

            imgui.separator()
            imgui.menu_item("class %s" % str(self.spec.cls), None, False, False)
            imgui.menu_item("node #%d" % self.window_id, None, False, False)
            imgui.end_popup()

        # handle clicking the node once it's selected as dragging
        if self.hovered and imgui.is_mouse_clicked(0) and not io.key_shift and interaction_allowed \
                and self.selected and not self.ui_graph.is_dragging_connection():
            # mark this node as being dragged
            self.dragging = True
            self.dragging_mouse_start = io.mouse_pos
            interacted = True
            # set for all selected nodes where they were at beginning of dragging
            for node in self.ui_graph.nodes:
                if node.selected:
                    node.dragging_node_start = node.actual_pos
        # stop dragging once mouse is released again
        if self.dragging and imgui.is_mouse_released(0):
            self.dragging = False
            self.dragging_mouse_start = None
            for node in self.ui_graph.nodes:
                node.dragging_node_start = None

        # draw border(s)
        with draw_on_channel(draw_list, CHANNEL_NODE_BACKGROUND):
            draw_list.add_rect(upper_left, lower_right, COLOR_NODE_BORDER, 0.0)
            if self.hovered:
                draw_list.add_rect(upper_left_hover, lower_right_hover, COLOR_NODE_BORDER_HOVERED, 0.0)
            if self.selected:
                draw_list.add_rect(upper_left_selection, lower_right_selection, COLOR_NODE_BORDER_SELECTED, 0.0, 0xF, 3.0)

        imgui.pop_id()
        imgui.set_cursor_pos(old_cursor_pos)

        # if the node's position should be set such that a port is at a specific position...
        if self._align_port_id is not None:
            # set node position only after one frame where correct size is determined
            if self._align_port_counter > 0:
                self._align_port_counter -= 1
            else:
                port_id = self._align_port_id
                port_pos0 = self.get_port_position(port_id)
                port_pos1 = self._align_port_pos

                offset = t_sub(port_pos1, port_pos0)
                self.pos = t_add(self.pos, offset)
                self.ui_graph.update_node_ui_state(self)

                self._align_port_id = None
                self._align_port_pos = None
                self._align_port_counter = 0

        return interacted

# data that needs to be shared across rendered ui graphs
class UIGraphData:
    def __init__(self, base_node, settings):
        # information about which node types are available
        self.base_node = base_node
        self.node_specs = []
        self.filtered_node_specs = []
        self.update_available_nodes()

        # shared clipboard among graphs
        self.graph_clipboard = None

        # shared style information
        self.background_alpha = settings.get("bg_alpha", 0.2)
        self.grid_alpha = settings.get("grid_alpha", 0.0)
        self.node_bg_alpha = settings.get("node_bg_alpha", 0.75)
        self.node_alpha = settings.get("node_alpha", 1.0)

    def get_settings(self):
        settings = {}
        settings["bg_alpha"] = self.background_alpha
        settings["grid_alpha"] = self.grid_alpha
        settings["node_bg_alpha"] = self.node_bg_alpha
        settings["node_alpha"] = self.node_alpha
        return settings

    # search for node types that have input/output port with specific dtype
    # and put them into filtered_node_specs
    def filter_available_nodes(self, dtype, is_input):
        def has_specific_port(node_spec):
            ports = node_spec.inputs if is_input else node_spec.outputs
            return any([ port_spec["dtype"] == dtype for port_spec in ports ])

        self.filtered_node_specs = [ node_spec for node_spec in self.node_specs if has_specific_port(node_spec) ]

    def update_available_nodes(self):
        # sort by node categories and then by names
        node_types = self.base_node.get_subclass_nodes(include_self=False)
        node_types.sort(key=lambda n: n.spec.name)
        node_types.sort(key=lambda n: n.spec.options["category"])

        self.node_specs = [ n.spec for n in node_types if not n.spec.options["virtual"] ]

class SubgraphHandler:
    def open_subgraph(self, name, graph, parent_graph):
        pass

    def remove_subgraph(self, graph):
        pass

class UIGraph(NodeGraphListener):
    def __init__(self, graph, ui_graph_data, subgraph_handler):
        self.graph = graph
        self.graph.add_listener(self)

        self.ui_offset = (0, 0)
        self.ui_nodes = {}
        self.ui_connections = []
        self.ui_graph_data = ui_graph_data

        # handler for subgraph things, must be instance of SubgraphHandler
        self.subgraph_handler = subgraph_handler

        self.reset_cached_counter = 0

        # current z index
        # gets incremented each time node is created / bumped to foreground
        self.nodes_z_index = 0

        # window position in screen space
        # set in each call to show
        self.pos = None
        self.size = None

        # interaction state
        # if user is dragging a connection: this is the ui connection object
        self.dragging_connection = None
        self.dragging_target_port_type = None
        # there can be a connection that should be deleted after dragging new connection
        self.dragging_connection_to_remove = None
        # whether user is dragging position
        self.dragging_position = False
        # whether user is making a selection
        self.dragging_selection = False
        self.selection_start = None
        # save position where context menu was opened
        # (for spawning nodes exactly where menu was opened)
        self.context_mouse_pos = None
        self.context_search_text = ""
        self.context_search_text = ""

        self.io = imgui.get_io()
        self.key_map = list(self.io.key_map)

        # generate events for all nodes/connections that already exist in the graph
        # TODO at some point perhaps move this to graph
        for instance in self.graph.instances:
            ui_data = self.graph.node_ui_data[instance.id]
            self.created_node(self.graph, instance, ui_data)
        for src_node, connections in self.graph.connections_from.items():
            for src_port_id, dst_node, dst_node_id in connections:
                self.created_connection(self.graph, src_node, src_port_id, dst_node, dst_node_id)
        self.changed_ui_data(self.graph, self.graph.ui_data)
    #
    # coordinate conversions
    #
    
    def local_to_window(self, pos):
        offset = self.ui_offset
        return pos[0] - offset[0], pos[1] - offset[1]
    def local_to_screen(self, pos):
        offset = self.ui_offset
        return self.pos[0] + pos[0] - offset[0], self.pos[1] + pos[1] - offset[1]
    def screen_to_local(self, pos):
        offset = self.ui_offset
        return pos[0] - self.pos[0] + offset[0], pos[1] - self.pos[1] + offset[1]

    #
    # node graph handlers
    #

    def changed_ui_data(self, graph, ui_data):
        self.ui_offset = ui_data.get("offset", (0, 0))

        self.reset_cached_positions()

    def created_node(self, graph, node, ui_data):
        ui_node = UINode(self, node, ui_data)
        self.ui_nodes[node.id] = ui_node

        if self.is_dragging_connection():
            dtype = self.dragging_connection.dtype
            mouse_node = self.dragging_connection.mouse_node
            # whether loose end / "mouse node" of the connection is an input
            is_input = self.dragging_connection.dst_node == mouse_node

            # search for possible port that can be connected to the connection
            # TODO consider base types too?
            port_ids = []
            for port_id, port_spec in node.ports.items():
                if node_meta.is_input(port_id) == is_input and port_spec["dtype"] == dtype:
                    port_ids.append(port_id)

            assert len(port_ids) > 0
            # TODO allow choosing a port or use better heuristic!
            port_id = port_ids[0]
            if "i_input" in port_ids:
                port_id = "i_input"

            # finish the connection and align node so that port is that connection position
            self.finish_dragging_connection(ui_node, port_id)
            ui_node.align_port_at(port_id, mouse_node.get_port_position(None))

    def removed_node(self, graph, node):
        assert node.id in self.ui_nodes
        if node.HAS_SUBGRAPH:
            self.subgraph_handler.remove_subgraph(node.subgraph)
        del self.ui_nodes[node.id]

    def changed_node_ui_data(self, graph, node, ui_data):
        assert node.id in self.ui_nodes

        ui_node = self.ui_nodes[node.id]
        if "pos" in ui_data:
            ui_node.pos = ui_data["pos"]
        if "selected" in ui_data:
            ui_node.selected = ui_data["selected"]

        self.reset_cached_positions()

    def created_connection(self, graph, src_node, src_port_id, dst_node, dst_port_id):
        src_node = self.ui_nodes[src_node.id]
        dst_node = self.ui_nodes[dst_node.id]
        self.ui_connections.append(UIConnection(self, src_node, src_port_id, dst_node, dst_port_id))

    def removed_connection(self, graph, src_node, src_port_id, dst_node, dst_port_id):
        src_node = self.ui_nodes[src_node.id]
        dst_node = self.ui_nodes[dst_node.id]

        for c in self.ui_connections:
            if (c.src_node, c.src_port_id, c.dst_node, c.dst_port_id) \
                != (src_node, src_port_id, dst_node, dst_port_id):
                continue
            c.disconnect()
            self.ui_connections.remove(c)
            return
        assert False, "No ui connection found to remove"

    #
    # callbacks from ui nodes / user interaction logic
    # update state of graph according to changed ui data
    #

    def update_ui_state(self):
        self.graph.set_ui_data({"offset" : self.ui_offset})

        self.reset_cached_positions()

    def update_node_ui_state(self, node):
        # node is a ui node object
        ui_data = {}
        ui_data["pos"] = node.pos
        ui_data["collapsed"] = node.collapsed
        ui_data["selected"] = node.selected
        self.graph.set_node_ui_data(node.instance, ui_data)

        self.reset_cached_positions()

    #
    # editor api functions used by ui nodes, connections and user interaction logic
    #

    @property
    def nodes(self):
        return self.ui_nodes.values()

    @property
    def selected_nodes(self):
        return filter(lambda node: node.selected, self.nodes)

    def touch_z_index(self):
        i = self.nodes_z_index
        self.nodes_z_index += 1
        return i

    def reset_cached_positions(self):
        # HACK
        # need to update it for multiple frames for connections to receive right position on toggle collapse node
        self.reset_cached_counter = 3

    def is_key_down(self, key):
        io = self.io
        return io.is_key_down(key) and io.get_key_down_duration(key) == 0.0

    def remove_node(self, node):
        self.graph.remove_node(node.instance)

    def remove_connection(self, connection):
        c = connection
        self.graph.remove_connection(c.src_node.instance, c.src_port_id, c.dst_node.instance, c.dst_port_id)

    def drag_connection(self, node, port_id, remove_connection=None):
        # remove_connection can be a connection that should be removed after dragging this connection
        assert self.dragging_connection is None
        self.dragging_connection = UIConnection.create(self, node, port_id)
        self.dragging_target_port_type = not node_meta.is_input(port_id)
        self.dragging_connection_to_remove = remove_connection

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
        if node_meta.is_input(port_id) and len(node.ui_connections[port_id]) != 0:
            return False

        port_spec = node.instance.ports[port_id]
        connection = self.dragging_connection
        other_port_spec = None
        if node_meta.is_input(port_id):
            other_port_spec = connection.src_node.instance.ports[connection.src_port_id]
        else:
            other_port_spec = connection.dst_node.instance.ports[connection.dst_port_id]
        return port_spec["dtype"].base_type == other_port_spec["dtype"].base_type

    def finish_dragging_connection(self, node, port_id):
        assert self.is_dragging_connection()
        assert self.is_connection_droppable(node, port_id)

        if self.dragging_connection_to_remove is not None:
            self.remove_connection(self.dragging_connection_to_remove)
            self.dragging_connection_to_remove = None

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

    def abort_dragging_connection(self):
        if self.is_dragging_connection():
            self.dragging_connection.disconnect()
            self.dragging_connection = None

    #
    # selection management
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
            self.update_node_ui_state(node)

    #
    # actual graph rendering
    #

    def show_context_menus(self, create_node_from_connection=False):
        self.show_context_menu_create(create_node_from_connection)
        self.show_context_menu_search()

    def show_context_menu_create(self, create_node_from_connection):
        io = self.io

        just_opened_popup = False
        reopen_popup = False

        # note about the last condition:
        # - don't allow right-click on top of another node to open context menu
        # - BUT: if you drag a new connection on top of another node, the context menu should still open
        no_node_hovered = lambda: not any(map(lambda n: n.hovered, self.nodes))
        if imgui.is_window_hovered() \
                and (imgui.is_mouse_clicked(1) or create_node_from_connection) \
                and (create_node_from_connection or no_node_hovered()):
            context_name = "context_create"
            if io.key_shift and not create_node_from_connection:
                context_name = "context_import"
            # remember where context menu was opened
            # (to place node there)
            self.context_mouse_pos = io.mouse_pos
            imgui.open_popup(context_name)
            self.context_search_text = ""
            self.context_create_index = 0
            just_opened_popup = True

        if imgui.begin_popup("context_create"):
            assert self.context_mouse_pos is not None
            # handle when user right-clicked outside of the popup
            # this should close the popup and re-open it at the new position
            # re-opening must be handled outside of begin_popup()/end_popup()
            # NOTE: is_window_hovered doesn't work for popups. so right-clicking inside the popup will work too, but who cares
            if not just_opened_popup and imgui.is_mouse_clicked(1):
                self.abort_dragging_connection()
                reopen_popup = True

            # set keyboard focus only once
            if not imgui.is_any_item_active():
                imgui.set_keyboard_focus_here()
            imgui.push_item_width(250)
            changed, self.context_search_text = imgui.input_text("", self.context_search_text, 255, imgui.INPUT_TEXT_ENTER_RETURNS_TRUE)

            def filter_nodes(text):
                filtered = []

                # use a set of filtered nodes when creating a node from a connection
                node_specs = self.ui_graph_data.node_specs
                if self.is_dragging_connection():
                    node_specs = self.ui_graph_data.filtered_node_specs

                for i, spec in enumerate(node_specs):
                    label = "%s (%s)" % (spec.name, spec.module_name)
                    contained, n = match_substring_partly(text.lower(), label.lower())
                    if contained:
                        filtered.append((n, (label, spec, {})))

                    for name, preset_values in spec.cls.get_presets(self.graph):
                        label = "%s: %s (%s)" % (spec.name, name, spec.module_name)
                        contained, n = match_substring_partly(text.lower(), label.lower())
                        if contained:
                            filtered.append((n, (label, spec, preset_values)))

                filtered.sort(key = lambda item: item[0])
                return [ item[1] for item in filtered ]

            entries = filter_nodes(self.context_search_text)

            if self.is_key_down(glfw.GLFW_KEY_UP):
                self.context_create_index -= 1
            if self.is_key_down(glfw.GLFW_KEY_DOWN):
                self.context_create_index += 1
            if self.is_key_down(glfw.GLFW_KEY_ESCAPE):
                # make sure to remove dragged connection (if any)
                self.abort_dragging_connection()
                imgui.close_current_popup()

            self.context_create_index = max(0, min(len(entries) - 1, self.context_create_index))
            selected = self.context_create_index
            imgui.listbox_header("", 250, 300)
            for i, (label, spec, preset_values) in enumerate(entries):
                imgui.push_id(i)
                is_selected = selected == 0
                imgui.selectable(label, is_selected)
                if imgui.is_item_clicked() or (is_selected and changed):
                    pos = self.screen_to_local(self.context_mouse_pos)
                    self.graph.create_node(spec, values=preset_values, ui_data={"pos" : pos})
                    # in case the node was created with dragging a connection, the connection will
                    # be connected where the ui node is created
                    # TODO it would be nice to set the mouse position back to where the node is now
                    imgui.close_current_popup()
                imgui.pop_id()
                selected -= 1
            if len(entries) == 0:
                imgui.text("Nothing found.")
            imgui.listbox_footer()
            imgui.separator()
            #clicked, self.show_test_window = imgui.menu_item("show demo window", None, self.show_test_window)
            #if clicked:
            #    imgui.set_window_focus("ImGui Demo")
            if imgui.menu_item("update node types")[0]:
                ShaderNodeLoader.reload_all()
                self.ui_graph_data.update_available_nodes()
            if imgui.menu_item("reset offset")[0]:
                self.ui_offset = (0, 0)
                self.update_ui_state()

            # is_mouse_clicked(0) here means that left mouse button was clicked outside of popup
            # popup will be closed then, so we have to remove the dragging connection (if any)
            if imgui.is_mouse_clicked(0):
                self.abort_dragging_connection()

            imgui.end_popup()

        import_path = node_widget.imgui_pick_file("context_import", assets.SAVE_PATH)
        if import_path is not None:
            offset = self.screen_to_local(self.context_mouse_pos)
            self.graph.import_file(import_path, pos_offset=offset)

        if reopen_popup:
            imgui.close_current_popup()
            imgui.open_popup("context_create")

    def show_context_menu_search(self):
        io = self.io

        if imgui.is_window_hovered() \
                and io.key_ctrl and self.is_key_down(glfw.GLFW_KEY_F):
            imgui.open_popup("context_search")
            self.context_mouse_pos = io.mouse_pos
            self.context_search_text = ""
            self.context_search_index = 0

        if imgui.begin_popup("context_search"):
            # set keyboard focus only once
            if not imgui.is_any_item_active():
                imgui.set_keyboard_focus_here()
            imgui.push_item_width(250)
            changed, self.context_search_text = imgui.input_text("", self.context_search_text, 255, imgui.INPUT_TEXT_ENTER_RETURNS_TRUE)

            def filter_nodes(text):
                filtered = []

                for i, ui_node in enumerate(self.ui_nodes.values()):
                    instance = ui_node.instance
                    spec = instance.spec
                    label = "%s #%d" % (instance.collapsed_node_title, instance.id)
                    contained, n = match_substring_partly(text.lower(), label.lower())
                    if contained:
                        filtered.append((n, (label, ui_node)))

                filtered.sort(key = lambda item: item[0])
                return [ item[1] for item in filtered ]

            entries = filter_nodes(self.context_search_text)

            if self.is_key_down(glfw.GLFW_KEY_UP):
                self.context_search_index -= 1
            if self.is_key_down(glfw.GLFW_KEY_DOWN):
                self.context_search_index += 1
            if self.is_key_down(glfw.GLFW_KEY_ESCAPE):
                imgui.close_current_popup()

            self.context_search_index = max(0, min(len(entries) - 1, self.context_search_index))
            selected = self.context_search_index
            imgui.listbox_header("", 250, 300)
            for i, (label, ui_node) in enumerate(entries):
                imgui.push_id(i)
                is_selected = selected == 0
                imgui.selectable(label, is_selected)
                # as soon as the search text is not empty, move view to search result node
                if imgui.is_item_clicked() or (is_selected and self.context_search_text != ""):
                    # move view so that the resulting node is displayed 200px left and up from context menu
                    mouse_pos = self.context_mouse_pos
                    self.ui_offset = t_sub(ui_node.pos, t_sub(mouse_pos, (200, 200)))
                    self.update_ui_state()
                    if changed:
                       imgui.close_current_popup()
                imgui.pop_id()
                selected -= 1
            if len(entries) == 0:
                imgui.text("Nothing found.")
            imgui.listbox_footer()
            imgui.end_popup()

    def show(self, draw_list):
        io = self.io

        # get position and size of window we're rendering graph in
        self.pos = imgui.get_window_position()
        self.size = imgui.get_window_size()

        # draw background color / grid
        with draw_on_channel(draw_list, CHANNEL_BACKGROUND):
            # draw graph background
            d = self.ui_graph_data
            draw_list.add_rect_filled(self.pos, t_add(self.pos, self.size), COLOR_EDITOR_BACKGROUND(d.background_alpha))

            if d.grid_alpha > 0.001:
                # how does the grid work?
                #   -> find local coords where we see first grid pos
                #   -> build grid from there
                # round n down to nearest divisor d: n - (n % d)
                # (grid_x0 / grid_y0 in local coordinates btw)
                offset = self.ui_offset
                grid_size = EDITOR_GRID_SIZE
                grid_x0 = int(offset[0] - (offset[0] % grid_size))
                grid_x1 = int(grid_x0 + self.size[0] + grid_size)
                grid_y0 = int(offset[1] - (offset[1] % grid_size))
                grid_y1 = int(grid_y0 + self.size[1] + grid_size)

                c = COLOR_EDITOR_GRID(d.grid_alpha)
                for x in range(grid_x0, grid_x1, grid_size):
                    draw_list.add_line(self.local_to_screen((x, grid_y0)), self.local_to_screen((x, grid_y1)), c)
                for y in range(grid_y0, grid_y1, grid_size):
                    draw_list.add_line(self.local_to_screen((grid_x0, y)), self.local_to_screen((grid_x1,  y)), c)

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

        rendered_connections = 0
        rendered_nodes = 0

        # draw / handle nodes and connections
        imgui.push_style_var(imgui.STYLE_ALPHA, self.ui_graph_data.node_alpha)
        for connection in self.ui_connections:
            if not connection.is_visible():
                continue
            rendered_connections += 1
            connection.show(draw_list)

        # little hack: to get overlapping nodes and such correct,
        #    render nodes in an order. nodes request a new z-index from the
        #    editor when they got touched and should be in the foreground again
        interaction_allowed = not io.key_shift
        for node in sorted(self.nodes, key=lambda n: n.z_index):
            if not node.is_visible():
                continue

            rendered_nodes += 1
            with draw_on_channel(draw_list, CHANNEL_NODE):
                if not interaction_allowed:
                    imgui.push_item_flag(imgui.ITEM_DISABLED, True)
                interacted = node.show(draw_list, interaction_allowed)
                if not interaction_allowed:
                    imgui.pop_item_flag()
                interaction_allowed = interaction_allowed and not interacted

            # TODO
            # unfortunately we have to merge and split the draw list multiple times for that
            # maybe there is a better way
            draw_list.channels_merge()
            draw_list.channels_split(CHANNEL_COUNT)
            draw_list.channels_set_current(CHANNEL_DEFAULT)
        if self.dragging_connection is not None:
            self.dragging_connection.reset_position()
            self.dragging_connection.show(draw_list)
        imgui.pop_style_var()

        if self.reset_cached_counter:
            for connection in self.ui_connections:
                connection.reset_position()
            for node in self.nodes:
                node.reset_position()
            self.reset_cached_counter = max(0, self.reset_cached_counter - 1)

        # dropping connection to ports is handled by nodes
        # we're checking here if a connection was dropped into nowhere
        create_node_from_connection = False
        if self.is_dragging_connection() and imgui.is_mouse_released(0):
            c = self.dragging_connection
            assert c.p0 is not None
            assert c.p1 is not None
            d = (c.p0[0] - c.p1[0])**2 + (c.p0[1] - c.p1[1]) ** 2
            # if the connection was dragged a bit (at least 50px), let the user create a new node here
            # which gets attached to the connection directly
            if d > 50**2 and not io.key_shift:
                # make connection stay at the current position
                mouse_node = self.dragging_connection.mouse_node
                mouse_node.keep_position()

                # filter currently available nodes
                dtype = self.dragging_connection.dtype
                is_input = self.dragging_connection.dst_node == mouse_node
                self.ui_graph_data.filter_available_nodes(dtype, is_input)

                create_node_from_connection = True
            else:
                self.abort_dragging_connection()

            if self.dragging_connection_to_remove is not None:
                self.remove_connection(self.dragging_connection_to_remove)
            self.dragging_connection_to_remove = None

        # handle a starting selection
        # it's important that ctrl is not pressed (ctrl is for dragging position)
        # and that no node is being dragged
        no_node_dragging = lambda: not any([ node.dragging for node in self.nodes ])
        if imgui.is_window_hovered() and not self.is_dragging_connection() \
                and imgui.is_mouse_clicked(0) and not io.key_shift \
                and no_node_dragging():
            self.dragging_selection = True
            self.selection_start = self.screen_to_local(io.mouse_pos)

        # handle ending selection
        if self.dragging_selection and imgui.is_mouse_released(0):
            self.dragging_selection = False

        # handle different selection and node modifications for some shortcuts
        if imgui.is_window_hovered() and not imgui.is_any_item_active():
            key_map = self.key_map
            key_a = glfw.GLFW_KEY_A
            key_d = glfw.GLFW_KEY_D
            key_i = glfw.GLFW_KEY_I
            key_escape = key_map[imgui.KEY_ESCAPE]
            key_delete = key_map[imgui.KEY_DELETE]
            key_y = glfw.GLFW_KEY_Z
            key_p = glfw.GLFW_KEY_P
            key_x = glfw.GLFW_KEY_X
            key_f = glfw.GLFW_KEY_F

            # select all nodes
            if self.is_key_down(key_a):
                for node in list(self.nodes):
                    node.selected = True
                    self.update_node_ui_state(node)
            # invert selection
            if self.is_key_down(key_i):
                for node in list(self.nodes):
                    node.selected = not node.selected
                    self.update_node_ui_state(node)
            # select no nodes
            if self.is_key_down(key_escape):
                for node in list(self.nodes):
                    node.selected = False
                    self.update_node_ui_state(node)
            # delete selected nodes
            if self.is_key_down(key_delete) or self.is_key_down(key_d):
                for node in list(self.nodes):
                    if node.selected:
                        self.remove_node(node)

            d = self.ui_graph_data
            # copy selected nodes
            if self.is_key_down(key_y):
                d.graph_clipboard = self.graph.serialize_selected()
            # paste copied nodes
            if self.is_key_down(key_p):
                if d.graph_clipboard is not None:
                    offset = self.screen_to_local(io.mouse_pos)
                    self.graph.unserialize_as_selected(d.graph_clipboard, pos_offset=offset)
            # cut selected nodes
            if self.is_key_down(key_x):
                d.graph_clipboard = self.graph.serialize_selected()
                for node in list(self.nodes):
                    if node.selected:
                        self.remove_node(node)
            # duplicate selected nodes
            if self.is_key_down(key_f):
                self.graph.duplicate_selected((20, 20))

            # handle start dragging position with shift+click
            if not self.is_dragging_connection() \
                    and io.key_shift and imgui.is_mouse_clicked(0):
                self.dragging_position = True
        # update position
        if self.dragging_position:
            self.ui_offset = t_sub(self.ui_offset, imgui.get_mouse_drag_delta())
            self.update_ui_state()
            imgui.reset_mouse_drag_delta()
        # end of dragging position
        if self.dragging_position and imgui.is_mouse_released(0):
            self.dragging_position = False

        # show context
        self.show_context_menus(create_node_from_connection=create_node_from_connection)

        stats = {
            "connections" : (rendered_connections, len(self.ui_connections)),
            "nodes" : (rendered_nodes, len(self.ui_nodes))
        }
        return stats

class NodeEditor(SubgraphHandler):
    def __init__(self, base_node=node_meta.Node):
        super().__init__()

        # also UI graph representations share some data such as settings and clipboard
        # that's kept in this instance
        settings = self.load_settings()
        util.time.global_time.paused = settings.get("paused", False)
        self.ui_graph_data = UIGraphData(base_node=base_node, settings=settings)

        # opened graphs and UI representations
        self.graphs = []
        self.ui_graphs = []
        # some more information about graphs:
        # name, parent graph (index), last visited subgraph (index)
        # also: index of the last graph opened that wasn't the background graph
        # also important: when graphs are removed, their entries are all set to None
        #   (to not mess with the parent indices references etc.)
        self.graph_names = []
        self.parent_graphs = []
        self.last_visited_subgraph = []
        self.last_graph_not_background = 0

        # current graph / UI representation
        self.current_graph_index = None
        self.current_graph = None
        self.current_ui_graph = None

        # per default we have two graphs running in parallel:
        # - session graph, which is the main workspace, files should be loaded into this
        # - background graph, where the beat detection happens mostly
        self.root_graph = RootGraph()
        self.session_graph = NodeGraph()
        self.background_graph = NodeGraph()
        # also create graph traits handler before graphs are added
        # graph traits handles keeping track of special nodes like Renderer, Input values, etc.
        self.graph_traits = GraphTraits()
        self.add_graph("session", self.session_graph, add_to_root_graph=True)
        self.add_graph("background", self.background_graph, add_to_root_graph=True)
        self.set_graph(0)

        self.show_graph = settings.get("show_graph", True)
        self.show_external_window = settings.get("show_external_window", False)
        self.external_window_i3_handle = settings.get("external_window_i3_handle", False)
        self.external_window_i3_workspace = settings.get("external_window_i3_workspace", "")
        self.show_test_window = settings.get("show_test_window", False)
        self.hide_after_seconds = settings.get("hide_after_n_seconds", 5)
        self.output_value = settings.get("output_value", 1.0)
        self.output_aspect_zoom_out = settings.get("output_aspect_zoom_out", True)
        self.set_external_window_visibility(self.show_external_window)

        autoplay_settings = settings.get("autoplay", {})
        self.autoplay_wildcard = autoplay_settings.get("wildcard", "scenes/*.json")
        self.autoplay_interval = autoplay_settings.get("interval", 120.0)
        self.autoplay_fade_duration = autoplay_settings.get("fade_duration", 2.0)
        self.autoplay_enabled = False

        self.autoplay_current_interval = self.autoplay_interval
        self.autoplay_current_file = None
        # last remaining time of autoplay
        self.autoplay_last_remaining = self.autoplay_interval
        # time when autoplay was started last time
        self.autoplay_last_start = None
        # remaining autoplay time (if last_start != None): last_remaining - (time - last_start)

        # keep two functions that determine fading in/out
        # to get final alpha just get both values and multiply. one of them will always be 1
        self.autoplay_fade_in = lambda: 1.0
        self.autoplay_fade_out = lambda: min(1.0, self.autoplay_time / (self.autoplay_fade_duration + 0.0001))

        self.random_seed = ""

        # appearance states
        self.last_mouse_pos = None
        self.last_mouse_pos_changed = 0
        self.show_windows = True

        # shader program to render output texture
        vertex = assets.load_shader(path="common/passthrough.vert")
        fragment = assets.load_shader(path="common/passthrough_with_alpha.frag")
        self.texture_program = gloo.Program(vertex, fragment, count=4, version="130")
        self.texture_program["iPosition"] = [(-1,-1), (-1,+1), (+1,-1), (+1,+1)]
        self.texture_program["iTexCoord"] = [( 0, 1), ( 0, 0), ( 1, 1), ( 1, 0)]
        #self.texture_program["uModelViewProjection"] = np.eye(4, dtype=np.float32)
        self.texture_program["uTextureSize"] = np.float32([1.0, 1.0], dtype=np.float32)
        self.texture_program["uTransformUV"] = np.eye(4, dtype=np.float32)

        # performance measurement stuffs
        self.fps = 0.0
        self.editor_time = 0.0
        self.editor_time_relative = 0.0
        self.imgui_render_time = 0.0
        self.imgui_render_time_relative = 0.0
        self.processing_time = 0.0
        self.processing_time_relative = 0.0
        self.total_time = 0.0
        self.total_time_relative = 0.0

        self.io = imgui.get_io()
        self.key_map = list(self.io.key_map)

        if os.path.isfile("session.json"):
            self.session_graph.load_file("session.json")
        if os.path.isfile("background.json"):
            self.background_graph.load_file("background.json")

    #
    # misc stuff
    #

    def load_settings(self):
        path = "settings.json"
        if not os.path.isfile(path):
            return {}
       
        try: 
            return json.load(open(path))
        except json.JSONDecodeError:
            print("### Warning: Unable to load settings, see the exception below:")
            traceback.print_exc()

        # empty settings in case of an error
        return {}

    def write_settings(self):
        settings = {}
        settings["paused"] = util.time.global_time.paused
        settings["show_graph"] = self.show_graph
        settings["show_external_window"] = self.show_external_window
        settings["external_window_i3_handle"] = self.external_window_i3_handle
        settings["external_window_i3_workspace"] = self.external_window_i3_workspace
        settings["show_test_window"] = self.show_test_window
        settings["hide_after_seconds"] = self.hide_after_seconds
        settings["output_value"] = self.output_value
        settings["output_aspect_zoom_out"] = self.output_aspect_zoom_out
        settings.update(self.ui_graph_data.get_settings())

        autoplay = {}
        autoplay["wildcard"] = self.autoplay_wildcard
        autoplay["interval"] = self.autoplay_interval
        autoplay["fade_duration"] = self.autoplay_fade_duration
        settings["autoplay"] = autoplay
        
        f = open("settings.json", "w")
        json.dump(settings, f)
        f.close()

    def timing_callback(self, editor_time, imgui_render_time, processing_time):
        self.fps = app.clock.get_default().get_fps()
        self.editor_time = editor_time
        self.editor_time_relative = editor_time / (1.0 / self.fps)
        self.imgui_render_time = imgui_render_time
        self.imgui_render_time_relative = imgui_render_time / (1.0 / self.fps)
        self.processing_time = processing_time
        self.processing_time_relative = processing_time / (1.0 / self.fps)
        self.total_time = editor_time + imgui_render_time + processing_time
        self.total_time_relative = self.total_time / (1.0 / self.fps)

    def set_external_window_visibility(self, visible):
        if visible:
            external_window.show()
            if self.external_window_i3_handle:
                os.system("i3-msg '[title=\"pyvisual optics external\"] move to workspace %s'" % self.external_window_i3_workspace)
                os.system("i3-msg '[title=\"pyvisual optics external\"] fullscreen'")
            # only for glfw backend - beware
            window.focus()
        else:
            external_window.hide()

    @property
    def autoplay_time(self):
        autoplay_time = self.autoplay_last_remaining
        if self.autoplay_last_start is not None:
            autoplay_time -= time.time() - self.autoplay_last_start
        return autoplay_time

    def pick_next_autoplay_file(self):
        current = self.autoplay_current_file
        paths = glob.glob(os.path.join(assets.SAVE_PATH, self.autoplay_wildcard))
        assert len(paths) != 0

        def pick():
            path = random.choice(paths)
            if len(paths) != 1 and path == current:
                return pick()
            return path

        return pick()

    def draw_output_texture(self, target_size, is_external_output=False):
        texture = self.graph_traits.output_texture
        if texture is None:
            return

        autoplay_alpha = 1.0
        if self.autoplay_enabled:
            autoplay_alpha = self.autoplay_fade_in() * self.autoplay_fade_out()
        brightness = 1.0
        if is_external_output:
            brightness = self.output_value

        mvp = np.eye(4, dtype=np.float32)
        texture_size = texture.shape[:2][::-1]

        texture_aspect = texture_size[0] / texture_size[1]
        target_aspect = target_size[0] / target_size[1]

        if (texture_aspect < target_aspect) ^ self.output_aspect_zoom_out:
            # border left/right
            glm.scale(mvp, texture_aspect, 1.0, 1.0)
            glm.scale(mvp, 1.0 / target_aspect, 1.0, 1.0)
        else:
            # border top/bottom
            glm.scale(mvp, 1.0, 1.0 / texture_aspect, 1.0)
            glm.scale(mvp, 1.0, target_aspect, 1.0)


        gl.glViewport(0, 0, target_size[0], target_size[1])
        self.texture_program["uModelViewProjection"] = mvp
        self.texture_program["uInputTexture"] = texture
        self.texture_program["uValue"] = brightness
        self.texture_program["uAlpha"] = autoplay_alpha
        self.texture_program.draw(gl.GL_TRIANGLE_STRIP)

    #
    # graph management
    #

    def set_graph(self, index):
        self.current_graph_index = index
        self.current_graph = self.graphs[self.current_graph_index]
        self.current_ui_graph = self.ui_graphs[self.current_graph_index]
        self.current_ui_graph.reset_cached_positions()
        if index != 1:
            self.last_visited_graph_not_background = index

    def add_graph(self, name, graph, parent_index=None, add_to_root_graph=False):
        if graph in self.graphs:
            index = self.graphs.index(graph)
            return index

        index = len(self.graphs)
        # if no parent index is specified, the graph is top-level, i.e. its own parent
        if parent_index is None:
            parent_index = index

        # tell graph traits to have a look at special nodes of this graph
        self.graph_traits.add_graph(graph)
        # top-level graphs (session, background) need to be evaluated by the root graph
        if add_to_root_graph:
            self.root_graph.append(graph)

        # add graph / UI representation
        self.graphs.append(graph)
        self.ui_graphs.append(UIGraph(graph, self.ui_graph_data, self))

        # other information
        self.graph_names.append(name)
        self.parent_graphs.append(parent_index)
        self.last_visited_subgraph.append(index)
        return index

    def open_subgraph(self, name, graph, parent_graph):
        name = "subgraph " + name
        parent_index = self.graphs.index(parent_graph)
        index = self.add_graph(name, graph, parent_index)
        self.last_visited_subgraph[parent_index] = index
        self.set_graph(index)

    def remove_subgraph(self, graph):
        # is called even when a subgraph is not opened
        if graph not in self.graphs:
            # ignore the call in that case
            return
        index = self.graphs.index(graph)
        parent_index = self.parent_graphs[index]

        # clear graph to recognize the removal of that graph (for RenderNode's for example)
        graph.clear()

        # disable all entries
        self.graphs[index] = None
        self.ui_graphs[index] = None
        self.graph_names[index] = None
        self.parent_graphs[index] = -1
        if self.last_visited_subgraph[parent_index] == index:
            self.last_visited_subgraph[parent_index] = parent_index

        # remove child graphs of this graph
        for i in range(len(self.graphs)):
            if self.parent_graphs[i] == index:
                self.remove_subgraph(self.graphs[i])

        # switch to parent graph in case this graph is the current graph
        if self.current_graph_index == index:
            self.set_graph(self.parent_graphs[index])

    #
    # graph states
    #

    def reset_graphs(self):
        self.root_graph.apply_instances(lambda node: node.reset_preset())
        self.root_graph.apply_instances(lambda node: node.reset_state())

    def randomize_graphs(self):
        seed = self.random_seed.strip()
        try:
            seed = int(seed)
        except ValueError:
            pass
        if type(seed) == str and len(seed) == 0:
            seed = None

        random.seed(seed)
        self.root_graph.apply_instances(lambda node: node.randomize_preset())
        self.root_graph.apply_instances(lambda node: node.randomize_state())

    #
    # rendering and interaction handling
    #

    def is_key_down(self, key):
        io = self.io
        return io.is_key_down(key) and io.get_key_down_duration(key) == 0.0

    def show(self):
        # create editor window
        #profile.enable()

        io = self.io
        w, h = io.display_size

        # some styling and other flags
        imgui.set_next_window_position(0, 0)
        imgui.set_next_window_size(w, h)
        flags = imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_BRING_TO_FRONT_ON_FOCUS | imgui.WINDOW_NO_SCROLLBAR | imgui.WINDOW_NO_SCROLL_WITH_MOUSE
        pop_style_vars = lambda: imgui.pop_style_var(2)
        imgui.push_style_var(imgui.STYLE_WINDOW_BORDERSIZE, 0.0)
        imgui.push_style_var(imgui.STYLE_FRAME_ROUNDING, 0.0)
        imgui.push_style_color(imgui.COLOR_WINDOW_BACKGROUND, 0.0, 0.0, 0.0, 0.0)

        expanded, _ = imgui.begin("NodeEditor", False, flags)
        self.pos = imgui.get_window_position()
        self.size = imgui.get_window_size()

        # make only editor window have transparent background
        # thus pop the color from the stack again already
        imgui.pop_style_color()

        if not expanded:
            pop_style_vars()
            return

        # initialize draw list
        draw_list = imgui.get_window_draw_list()
        draw_list.channels_split(CHANNEL_COUNT)
        draw_list.channels_set_current(CHANNEL_DEFAULT)

        # show graph
        # if you're wondering where output texture in background comes from:
        # it's rendered in the render loop outside of the editor
        graph_stats = None
        if self.show_graph:
            graph_stats = self.current_ui_graph.show(draw_list)

        # make sure to not get triggered when pressing e inside a text field
        if not io.want_capture_keyboard and not io.want_text_input:
            if self.is_key_down(glfw.GLFW_KEY_E):
                # switch between background graph and other graph (like you would expect tab to work)
                # assumption: background graph is at index 1
                if self.current_graph_index == 1:
                    self.set_graph(self.last_visited_graph_not_background)
                else:
                    self.set_graph(1)
            if self.is_key_down(glfw.GLFW_KEY_W):
                # go to next parent graph
                # (top-level graph is parent of itself)
                parent = self.parent_graphs[self.current_graph_index]
                self.set_graph(parent)
            if self.is_key_down(glfw.GLFW_KEY_S):
                # go to a subgraph
                # either the one of currently selected node, or last one visitied from here
                selected = list(self.current_ui_graph.selected_nodes)
                if len(selected) == 1:
                    instance = selected[0].instance
                    if instance.HAS_SUBGRAPH:
                        name = instance.node_title
                        graph = instance.subgraph
                        parent_graph = self.current_ui_graph.graph
                        self.open_subgraph(name, graph, parent_graph)
                else:
                    subgraph = self.last_visited_subgraph[self.current_graph_index]
                    self.set_graph(subgraph)
        if self.is_key_down(glfw.GLFW_KEY_F3):
            self.show_graph = not self.show_graph
            self.last_mouse_pos_changed = time.time()
        if self.is_key_down(glfw.GLFW_KEY_F10):
            output_texture = self.graph_traits.output_texture
            if output_texture is not None:
                path = util.image.generate_screenshot_path()
                util.image.save_screenshot(output_texture.get(), path=path)
                self.session_graph.save_file(path.replace(".png", ".json"))

        if not io.want_capture_keyboard:
            if self.is_key_down(glfw.GLFW_KEY_SPACE):
                global_time = util.time.global_time
                global_time.paused = not global_time.paused
            if self.is_key_down(glfw.GLFW_KEY_R):
                self.randomize_graphs()

        draw_list.channels_merge()

        if self.show_windows or self.show_graph:
            pos = imgui.get_cursor_screen_pos()
            w, h = imgui.get_window_size()
            dock_padding = 0

            flags = imgui.WINDOW_NO_RESIZE | imgui.WINDOW_ALWAYS_AUTO_RESIZE
            flags_static = imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_ALWAYS_AUTO_RESIZE

            imgui.set_next_window_position(pos[0] + dock_padding, pos[1] + dock_padding)
            if self.show_graph and imgui.begin("io", False, flags_static):
                if imgui.button("clear"):
                    self.current_graph.clear()

                imgui.same_line()
                if imgui.button("save"):
                    imgui.open_popup("save")
                save_path = node_widget.imgui_pick_file("save", assets.SAVE_PATH)
                if save_path is not None:
                    self.current_graph.save_file(save_path)

                imgui.same_line()
                if imgui.button("load"):
                    imgui.open_popup("load")
                load_path = node_widget.imgui_pick_file("load", assets.SAVE_PATH)
                if load_path is not None:
                    self.current_graph.load_file(load_path)

                imgui.same_line()
                if imgui.button("import"):
                    imgui.open_popup("import")
                if imgui.is_item_hovered():
                    imgui.set_tooltip("You can also shift+right click to import nodes")
                import_path = node_widget.imgui_pick_file("import", assets.SAVE_PATH)
                if import_path is not None:
                    self.current_graph.import_file(import_path, self.screen_to_local(io.mouse_pos))

                imgui.same_line()
                if imgui.button("export"):
                    imgui.open_popup("export")
                export_path = node_widget.imgui_pick_file("export", assets.SAVE_PATH)
                if export_path is not None:
                    self.current_graph.export_file(export_path)

                if imgui.begin_combo("", self.graph_names[self.current_graph_index]):
                    for i in range(len(self.graphs)):
                        name = self.graph_names[i]
                        # when graphs are removed, their entries are just set to None, consider this
                        if name is None:
                            continue
                        is_selected = i == self.current_graph_index
                        if is_selected:
                            imgui.set_item_default_focus()
                        opened, selected = imgui.selectable(name, is_selected)
                        if opened:
                            self.set_graph(i)
                    imgui.end_combo()

                imgui.end()

            imgui.set_next_window_position(self.pos[0] + w - 10, pos[1] + dock_padding, imgui.ALWAYS, 1, 0)
            if imgui.begin("performance", False, flags_static):
                imgui.text("fps: %.2f" % self.fps)
                imgui.text("editor time: %.2f ms ~ %.2f%%" % (self.editor_time * 1000.0, self.editor_time_relative * 100.0))
                imgui.text("imgui render time: %.2f ms ~ %.2f%%" % (self.imgui_render_time * 1000.0, self.imgui_render_time_relative * 100.0))
                imgui.text("processing time: %.2f ms ~ %.2f%%" % (self.processing_time * 1000.0, self.processing_time_relative * 100.0))
                imgui.text("total: %.2f ms ~ %.2f%%" % (self.total_time * 1000.0, self.total_time_relative * 100.0))

                if util.time.global_time.paused:
                    imgui.text_colored("PAUSED", 1.0, 0.0, 0.0)
                else:
                    imgui.text("")

                if graph_stats is not None:
                    imgui.text("c: %d / %d n: %d / %d" % (graph_stats["connections"] + graph_stats["nodes"]))
                imgui.end()

            if imgui.begin("settings", False, flags):
                changed, self.show_graph = imgui.checkbox("show graph", self.show_graph)
                changed, self.show_external_window = imgui.checkbox("show external window", self.show_external_window)
                if changed:
                    self.set_external_window_visibility(self.show_external_window)
                changed, self.external_window_i3_handle = imgui.checkbox("external window move/fullscreen with i3", self.external_window_i3_handle)
                if self.external_window_i3_handle:
                    changed, self.external_window_i3_workspace = imgui.input_text("i3 workspace", self.external_window_i3_workspace, 256, imgui.INPUT_TEXT_ENTER_RETURNS_TRUE)

                changed, self.show_test_window = imgui.checkbox("show test window", self.show_test_window)
                changed, self.hide_after_seconds = imgui.input_int("hide ui after n seconds", self.hide_after_seconds, 5, 60)

                d = self.ui_graph_data
                changed, self.output_value = imgui.slider_float("output_value", self.output_value, 0.0, 1.0)
                changed, self.output_aspect_zoom_out= imgui.checkbox("aspect zoom out?", self.output_aspect_zoom_out)
                changed, d.background_alpha = imgui.slider_float("bg alpha", d.background_alpha, 0.0, 1.0)
                changed, d.grid_alpha = imgui.slider_float("grid alpha", d.grid_alpha, 0.0, 1.0)
                changed, d.node_alpha = imgui.slider_float("node alpha", d.node_alpha, 0.0, 1.0)
                changed, d.node_bg_alpha = imgui.slider_float("node bg alpha", d.node_bg_alpha, 0.0, 1.0)
                imgui.end()

            if imgui.begin("autoplay", False, flags):
                autoplay_time = self.autoplay_time

                changed, self.autoplay_wildcard = imgui.input_text("Files", self.autoplay_wildcard, 256, imgui.INPUT_TEXT_ENTER_RETURNS_TRUE)
                imgui.same_line()
                if imgui.button("Load..."):
                    imgui.open_popup("wildcard")
                wildcard = node_widget.imgui_pick_file("wildcard", assets.SAVE_PATH)
                if wildcard is not None:
                    self.autoplay_wildcard = os.path.relpath(wildcard, assets.SAVE_PATH)

                imgui.push_item_width(150)
                changed, self.autoplay_interval = imgui.input_float("interval", self.autoplay_interval, 30.0, 60.0)
                changed, self.autoplay_fade_duration = imgui.slider_float("fade duration", self.autoplay_fade_duration, 0.0, 10.0)
                changed, self.autoplay_enabled = imgui.checkbox("enable autoplay", self.autoplay_enabled)
                if changed and self.autoplay_enabled:
                    self.autoplay_last_start = time.time()
                elif changed and not self.autoplay_enabled:
                    self.autoplay_last_remaining = autoplay_time
                    self.autoplay_last_start = None

                imgui.separator()
                
                imgui.push_item_width(150)
                changed, value = imgui.input_float("remaining time", autoplay_time, 10.0, 60.0)
                if changed:
                    self.autoplay_last_remaining = value
                    if self.autoplay_last_start is not None:
                        self.autoplay_last_start = time.time()
                if imgui.button("change now"):
                    self.autoplay_last_remaining = self.autoplay_fade_duration
                    if self.autoplay_last_start is not None:
                        self.autoplay_last_start = time.time()

                imgui.end()

            if imgui.begin("misc", False, flags):
                if imgui.collapsing_header("time", flags=imgui.TREE_NODE_DEFAULT_OPEN)[0]:
                    global_time = util.time.global_time

                    paused = global_time.paused
                    changed, paused = imgui.checkbox("pause time (space)", paused)
                    # let's try to not call that setter too often
                    if changed:
                        global_time.paused = paused

                    changed, global_time.time_offset = imgui.drag_float("time offset", global_time.time_offset, 0.1)

                if imgui.collapsing_header("states & presets", flags=imgui.TREE_NODE_DEFAULT_OPEN)[0]:
                    changed, self.random_seed = imgui.input_text("random seed", self.random_seed, 255)

                    if imgui.button("reset"):
                        self.reset_graphs()
                    if imgui.button("randomize"):
                        self.randomize_graphs()
                imgui.end()

            if imgui.begin("scene properties", False, flags):
                value_changed = False
                for name, value in system_var.values.items():
                    widget = system_var.widgets[name]

                    imgui.push_id(name)
                    widget.show(value, read_only=False)
                    imgui.same_line()
                    imgui.text(name)
                    imgui.pop_id()

                    if name == "threshold" and io.is_key_down(glfw.GLFW_KEY_T):
                        factor = 0.01
                        if io.key_shift:
                            factor *= 5.0
                        value.value += io.mouse_wheel * factor
                    if name == "gain" and io.is_key_down(glfw.GLFW_KEY_G):
                        factor = 0.25
                        if io.key_shift:
                            factor *= 5.0
                        value.value += io.mouse_wheel * factor

                    value_changed = value_changed or value.has_changed()

                if value_changed:
                    system_var.notify_change()
                system_var.write_variables(force=False)

                imgui.end()

            if self.show_test_window:
                imgui.show_test_window()

        # check if mouse wasn't moved and we should hide windows after some time
        mouse_pos = io.mouse_pos
        t = time.time()
        if self.last_mouse_pos != mouse_pos:
            self.last_mouse_pos = mouse_pos
            self.last_mouse_pos_changed = t
            self.show_windows = True
            window.set_cursor_visible(True)
        if self.hide_after_seconds != -1 and t - self.last_mouse_pos_changed > self.hide_after_seconds:
            self.show_windows = False
            window.set_cursor_visible(False)

        # handle autoplay
        if self.autoplay_enabled:
            autoplay_time = self.autoplay_time
            if autoplay_time <= 0.0:
                self.autoplay_current_interval = self.autoplay_interval
                self.autoplay_last_remaining = self.autoplay_interval
                self.autoplay_last_start = time.time()
                # fade in from current time, not from autoplay_time
                # otherwise more fades might happen if remaining time is increased
                self.autoplay_fade_in = lambda start=self.autoplay_last_start: min(1.0, (time.time() - start) / (self.autoplay_fade_duration + 0.0001))
                self.session_graph.load_file(self.pick_next_autoplay_file())

        imgui.end()
        pop_style_vars()

editor = NodeEditor()

editor_time = 0.0
imgui_render_time = 0.0
processing_time = 0.0
time_count = 0
profile_time_count = 0

PROFILE_STATS = "--profile-nodes" in sys.argv

if "--paused" in sys.argv:
    util.time.global_time.paused = True

@window.event
def on_draw(event):
    global editor_time, imgui_render_time, processing_time, time_count, profile_time_count

    # evaluate nodes
    start = time.time()
    #profile.enable()
    editor.root_graph.evaluate(record_stats=PROFILE_STATS)
    processing_time += time.time() - start
    #profile.disable()

    # render editor
    window.clear()
    editor.draw_output_texture(window.get_size())

    start = time.time()
    #profile.enable()
    imgui_renderer.process_inputs()
    imgui.new_frame()

    editor.show()
    #profile.disable()
    editor_time += time.time() - start

    start = time.time()
    imgui.render()
    draw = imgui.get_draw_data()
    #profile.enable()
    imgui_renderer.render(draw)
    #profile.disable()
    imgui_render_time += time.time() - start

    # performance stats
    time_count += 1
    if time_count >= 60*2:
        editor.timing_callback(editor_time / time_count, imgui_render_time / time_count, processing_time / time_count)
        editor_time = 0.0
        imgui_render_time = 0.0
        processing_time = 0.0
        time_count = 0

    if PROFILE_STATS:
        profile_time_count += 1
        if profile_time_count >= 60*5:
            import tabulate
            stats_by_instance, stats_by_node_type = editor.root_graph.get_stats()
            print("=== Performance stats ===")
            total_average = 0.0
            rows = []
            for node, values in stats_by_node_type[:25]:
                rows.append([node, "%d" % values["count"], "%.2f" % (values["avg"] * 1000000.0), "%.2f%%" % (values["rel"] * 100.0), "%.2f%%" % (values["cum"] * 100.0)])
                total_average += values["avg"]
            for node, values in stats_by_node_type[25:]:
                total_average += values["avg"]
            print(tabulate.tabulate(rows, headers=["Node type", "count", "avg time (micros)", "rel time", "inv cum time"]))
            print("=== ===")
            print("Total average time per frame: %.2f ms" % (total_average * 1000))
            print("=== ===")
            profile_time_count = 0

@window.event
def on_resize(width, height):
    editor.current_ui_graph.reset_cached_positions()

@external_window.event
def on_draw(event):
    external_window.clear()
    editor.draw_output_texture(external_window.get_size(), is_external_output=True)

def on_key_press(key, modifier):
    if key == ord("Q"):
        editor.session_graph.save_file("session.json")
        editor.session_graph.stop()
        #editor.background_graph.save_file("background.json")
        editor.background_graph.stop()
        editor.write_settings()
        system_var.write_variables(force=True)
        #profile.dump_stats("profile.stats")
        sys.exit(0)

window.event(on_key_press)
external_window.event(on_key_press)

if __name__ == "__main__":
    window.show()
    # external window visibility is handled by editor
    #external_window.hide()
    app.run()
