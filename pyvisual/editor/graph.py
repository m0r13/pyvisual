import json
from collections import defaultdict, OrderedDict
import pyvisual.node.base as node_meta
from pyvisual.node import dtype

class NodeGraphListener:
    def changed_ui_data(self, ui_data):
        pass

    def created_node(self, node, ui_data):
        pass

    def removed_node(self, node):
        pass

    def changed_node_ui_data(self, node, ui_data):
        pass

    def created_connection(self, src_node, src_port_id, dst_node, dst_port_id):
        pass

    def removed_connection(self, src_node, src_port_id, dst_node, dst_port_id):
        pass

# prepare for serialization
def format_port_spec(port_spec):
    port_spec = dict(port_spec)
    port_spec["dtype"] = port_spec["dtype"].name
    return port_spec

def unformat_port_spec(port_spec):
    port_spec = dict(port_spec)
    dtype_name = port_spec["dtype"]
    port_spec["dtype"] = dtype.dtypes.get(dtype_name, None)
    assert port_spec["dtype"] is not None, "Unable to find dtype of name %s" % dtype_name
    return port_spec

class NodeGraph:
    def __init__(self):
        self.listeners = []

        self.ui_data = {}
        self.node_id_counter = 0
        self.nodes = {}
        self.node_ui_data = defaultdict(lambda: {})

        self.connections_from = defaultdict(lambda: set())
        self.connections_to = defaultdict(lambda: set())

    def _assign_node_id(self):
        i = self.node_id_counter
        self.node_id_counter += 1
        return i

    #
    # serialization
    #

    def serialize(self, node_filter=lambda node: True):
        # TODO validation!!

        nodes = []
        connections = []

        for node in self.nodes.values():
            if not node_filter(node):
                continue
            node_data = {}
            node_data["id"] = node.id
            node_data["type"] = node.spec.name
            node_data["ui_data"] = self.node_ui_data[node.id]

            manual_values = {}
            for port_id, value in node.values.items():
                port_spec = node.ports[port_id]
                dtype = port_spec["dtype"]
                if isinstance(value, node_meta.InputValueHolder):
                    value = value.manual_value
                manual_values[port_id] = dtype.base_type.serialize(value.value)
            node_data["manual_values"] = manual_values

            custom_ports = []
            for port_id, port_spec in node.custom_ports.items():
                custom_ports.append((port_id, format_port_spec(port_spec)))
            node_data["custom_ports"] = custom_ports

            nodes.append(node_data)

        for src_node, outgoing_connections in self.connections_from.items():
            for (src_port_id, dst_node, dst_port_id) in outgoing_connections:
                if not node_filter(src_node) or not node_filter(dst_node):
                    continue
                connection_data = {}
                connection_data["src_node_id"] = src_node.id
                connection_data["src_port_id"] = src_port_id
                connection_data["dst_node_id"] = dst_node.id
                connection_data["dst_port_id"] = dst_port_id
                connections.append(connection_data)

        data = {"ui_data" : self.ui_data, "nodes" : nodes, "connections" : connections}
        return json.dumps(data, sort_keys=True, indent=4)

    def unserialize(self, data, as_selected=False, pos_offset=(0, 0), pos_normalize=True):
        # unserializes nodes/connections that are serialized in data string
        # as_selected means that new nodes will be selected (other nodes will be unselected)
        # pos_offset is added to positions of all new nodes
        # if pos_normalize is true, nodes are moved so that minimum coordinate of all nodes is pos_offset
        # if pos_normalize is false, pos_offset is just added to positions of all new nodes

        # TODO validation!!

        data = json.loads(data)

        if not as_selected:
            self.set_ui_data(data.get("ui_data", {}), notify=True)

        id_map = {}
        ignore_ids = set()
        new_nodes = []
        for node_data in data.get("nodes", []):
            assert "id" in node_data
            node_save_id = node_data["id"]
            assert not node_save_id in id_map

            spec = None
            try:
                spec = node_meta.NodeSpec.from_name(node_data["type"])
            except node_meta.NodeTypeNotFound as e:
                print("### Warning: Unable to find node type %s for node #%d. Ignoring it." % (node_data["type"], node_save_id))
                ignore_ids.add(node_save_id)
                continue

            node = self.create_node(spec, node_data["ui_data"])
            new_nodes.append(node)
            id_map[node_save_id] = node.id

            for port_id, port_spec in node_data.get("custom_ports", []):
                port_spec = unformat_port_spec(port_spec)

                if node_meta.is_input(port_id):
                    node.custom_input_ports[port_id] = port_spec
                else:
                    node.custom_output_ports[port_id] = port_spec
            node.update_ports()

            for port_id, json_value in node_data.get("manual_values", {}).items():
                if port_id not in node.ports:
                    print("### Warning: Unknown port %s of node %s #%d (trying to set manual value). Ignoring it." % (port_id, spec.name, node_save_id))
                    continue
                port_spec = node.ports[port_id]
                dtype = port_spec["dtype"]
                node.initial_manual_values[port_id] = dtype.base_type.unserialize(json_value)

        # handle new nodes being 
        if as_selected:
            assert pos_offset is not None

            # find minimum coordinates of all new nodes
            min_pos = 0, 0
            if pos_normalize:
                min_pos = float("inf"), float("inf")
                for node in new_nodes:
                    ui_data = self.node_ui_data[node.id]
                    assert "pos" in ui_data
                    pos = ui_data["pos"]
                    min_pos = min(pos[0], min_pos[0]), min(pos[1], min_pos[1])

            # unselect all nodes
            for node_id, ui_data in self.node_ui_data.items():
                node = self.nodes[node_id]
                ui_data = self.node_ui_data[node_id]
                if ui_data["selected"]:
                    ui_data["selected"] = False
                    self.set_node_ui_data(node, ui_data, notify=True)

            # select new nodes and apply position offset
            for node in new_nodes:
                ui_data = self.node_ui_data[node.id]
                pos = ui_data["pos"]
                pos = -min_pos[0] + pos[0] + pos_offset[0], -min_pos[1] + pos[1] + pos_offset[1]
                ui_data["pos"] = pos
                ui_data["selected"] = True
                self.set_node_ui_data(node, ui_data, notify=True)

        for connection_data in data.get("connections", []):
            src_node_id = connection_data["src_node_id"]
            dst_node_id = connection_data["dst_node_id"]
            src_port_id = connection_data["src_port_id"]
            dst_port_id = connection_data["dst_port_id"]

            if src_node_id in ignore_ids or dst_node_id in ignore_ids:
                print("### Warning: Ignoring connection %s (node #%d) -> %s (node #%d) because at least one node is to be ignored." \
                        % (src_port_id, src_node_id, dst_port_id, dst_node_id))
                continue

            src_node_id = id_map[src_node_id]
            dst_node_id = id_map[dst_node_id]

            src_node = self.nodes[src_node_id]
            dst_node = self.nodes[dst_node_id]
            if src_port_id not in src_node.ports:
                print("### Warning: Ignoring connection %s (node #%d) -> %s (node #%d) because source port %s does not exist." \
                        % (src_port_id, src_node_id, dst_port_id, dst_node_id, src_port_id))
                continue
            if dst_port_id not in dst_node.ports:
                print("### Warning: Ignoring connection %s (node #%d) -> %s (node #%d) because destination port %s does not exist." \
                        % (src_port_id, src_node_id, dst_port_id, dst_node_id, dst_port_id))
                continue
            self.create_connection(src_node, src_port_id, dst_node, dst_port_id)

    def serialize_selected(self):
        def node_filter(node):
            return self.node_ui_data[node.id]["selected"]
        return self.serialize(node_filter)

    def unserialize_as_selected(self, data, pos_offset=None):
        self.unserialize(data, as_selected=True, pos_offset=pos_offset)

    def duplicate_selected(self, pos_offset):
        data = self.serialize_selected()
        self.unserialize(data, as_selected=True, pos_offset=pos_offset, pos_normalize=False)

    def save_file(self, path):
        data = self.serialize()

        f = open(path, "w")
        f.write(data)
        f.close()

    def load_file(self, path):
        f = open(path, "r")
        data = f.read()
        f.close()

        self.clear()
        self.unserialize(data)

    def import_file(self, path, pos_offset):
        f = open(path, "r")
        data = f.read()
        f.close()

        self.unserialize(data, as_selected=True, pos_offset=pos_offset)

    def export_file(self, path):
        data = self.serialize_selected()

        f = open(path, "w")
        f.write(data)
        f.close()

    #
    # functions for changing node graph
    #

    def set_ui_data(self, ui_data, notify=False):
        self.ui_data = ui_data
        if notify:
            for listener in self.listeners:
                listener.changed_ui_data(ui_data)

    def create_node(self, spec, ui_data):
        node = spec.instantiate_node()
        node.id = self._assign_node_id()
        node.start(self)

        self.nodes[node.id] = node
        self.node_ui_data[node.id] = ui_data
        for listener in self.listeners:
            listener.created_node(node, ui_data)
        return node

    def remove_node(self, node):
        assert node.id in self.nodes and self.nodes[node.id] == node
        node.stop()

        # remove all connections from / to this node
        for src_port_id, dst_node, dst_port_id in set(self.connections_from[node]):
            self.remove_connection(node, src_port_id, dst_node, dst_port_id)
        for dst_port_id, src_node, src_port_id in set(self.connections_to[node]):
            self.remove_connection(src_node, src_port_id, node, dst_port_id)
        del self.nodes[node.id]
        del self.node_ui_data[node.id]

        for listener in self.listeners:
            listener.removed_node(node)

    def set_node_ui_data(self, node, ui_data, notify=False):
        self.node_ui_data[node.id] = ui_data

        if notify:
            for listener in self.listeners:
                listener.changed_node_ui_data(node, ui_data)

    def create_connection(self, src_node, src_port_id, dst_node, dst_port_id):
        input_value = dst_node.get_value(dst_port_id)
        assert input_value.connected_node is None
        input_value.connect(src_node, src_port_id)

        self.connections_from[src_node].add((src_port_id, dst_node, dst_port_id))
        self.connections_to[dst_node].add((dst_port_id, src_node, src_port_id))

        for listener in self.listeners:
            listener.created_connection(src_node, src_port_id, dst_node, dst_port_id)

    def remove_connection(self, src_node, src_port_id, dst_node, dst_port_id):
        input_value = dst_node.get_value(dst_port_id)
        assert input_value.connected_node == src_node
        input_value.disconnect()

        self.connections_from[src_node].remove((src_port_id, dst_node, dst_port_id))
        self.connections_to[dst_node].remove((dst_port_id, src_node, src_port_id))

        for listener in self.listeners:
            listener.removed_connection(src_node, src_port_id, dst_node, dst_port_id)

    def clear(self):
        for instance in list(self.nodes.values()):
            self.remove_node(instance)
        self.node_ui_counter = 0

    # selection management

    #
    # public methods
    #

    @property
    def instances(self):
        return self.nodes.values()

    @property
    def sorted_instances(self):
        instances = list(self.nodes.values())
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

    def evaluate(self, reset_instances=True):
        instances, _ = self.sorted_instances
        active_instances = set()
        for instance in instances:
            if instance.evaluate():
                active_instances.add(instance)
        # reset evaluation status and set all inputs/outputs unchanged!
        # if you want to evaluate outputs (for example Module node wants this),
        # pass reset_instances=False and call reset_instances() later manually
        if reset_instances:
            self.reset_instances()
        return active_instances

    def reset_instances(self):
        for instance in self.instances:
            instance.evaluated = False

    def stop(self):
        for instance in self.nodes.values():
            instance.stop()
