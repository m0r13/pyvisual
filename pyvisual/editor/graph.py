import json
from collections import defaultdict
import pyvisual.node.base as node_meta

class NodeGraphListener:
    def created_node(self, node, ui_data):
        pass

    def removed_node(self, node):
        pass

    def created_connection(self, src_node, src_port_id, dst_node, dst_port_id):
        pass

    def removed_connection(self, src_node, src_port_id, dst_node, dst_port_id):
        pass

class NodeGraph:
    def __init__(self):
        self.listeners = []

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

    def serialize(self):
        # TODO validation!!

        nodes = []
        connections = []

        for node in self.nodes.values():
            node_data = {}
            node_data["id"] = node.id
            node_data["type"] = node.spec.name
            node_data["ui_data"] = self.node_ui_data[node.id]

            manual_values = {}
            for port_name, value in node.inputs.items():
                port_id = "i_" + port_name
                port_spec = node.ports[port_id]
                dtype = port_spec["dtype"]
                manual_values[port_name] = dtype.base_type.serialize(value.manual_value.value)
            node_data["manual_values"] = manual_values

            nodes.append(node_data)

        for src_node, outgoing_connections in self.connections_from.items():
            for (src_port_id, dst_node, dst_port_id) in outgoing_connections:
                connection_data = {}
                connection_data["src_node_id"] = src_node.id
                connection_data["src_port_id"] = src_port_id
                connection_data["dst_node_id"] = dst_node.id
                connection_data["dst_port_id"] = dst_port_id
                connections.append(connection_data)

        data = {"nodes" : nodes, "connections" : connections}
        return json.dumps(data, sort_keys=True, indent=4)

    def unserialize(self, data):
        # TODO validation!!

        data = json.loads(data)

        id_map = {}
        for node_data in data.get("nodes", []):
            assert not node_data["id"] in id_map
            spec = node_meta.NodeSpec.from_name(node_data["type"])
            node = self.create_node(spec, node_data["ui_data"])
            id_map[node_data["id"]] = node.id

            for port_name, json_value in node_data.get("manual_values", {}).items():
                port_id = "i_" + port_name
                port_spec = node.ports[port_id]
                dtype = port_spec["dtype"]
                node.inputs[port_name].manual_value.value = dtype.base_type.unserialize(json_value)

        for connection_data in data.get("connections", []):
            src_node_id = id_map[connection_data["src_node_id"]]
            src_port_id = connection_data["src_port_id"]
            dst_node_id = id_map[connection_data["dst_node_id"]]
            dst_port_id = connection_data["dst_port_id"]

            src_node = self.nodes[src_node_id]
            dst_node = self.nodes[dst_node_id]
            self.create_connection(src_node, src_port_id, dst_node, dst_port_id)

    def save(self, path):
        data = self.serialize()

        f = open(path, "w")
        f.write(data)
        f.close()

    def load(self, path, append=False):
        f = open(path, "r")
        data = f.read()
        f.close()

        if not append:
            self.clear()
        self.unserialize(data)

    #
    # functions for changing node graph
    #

    def create_node(self, spec, ui_data):
        node = spec.instantiate_node()
        node.id = self._assign_node_id()
        node.start()

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

        for listener in self.listeners:
            listener.removed_node(node)

    def set_node_ui_data(self, node, ui_data):
        self.node_ui_data[node.id] = ui_data

    def create_connection(self, src_node, src_port_id, dst_node, dst_port_id):
        input_value = dst_node.inputs[node_meta.port_name(dst_port_id)]
        assert input_value.connected_node is None
        input_value.connect(src_node, node_meta.port_name(src_port_id))

        self.connections_from[src_node].add((src_port_id, dst_node, dst_port_id))
        self.connections_to[dst_node].add((dst_port_id, src_node, src_port_id))

        for listener in self.listeners:
            listener.created_connection(src_node, src_port_id, dst_node, dst_port_id)

    def remove_connection(self, src_node, src_port_id, dst_node, dst_port_id):
        input_value = dst_node.inputs[node_meta.port_name(dst_port_id)]
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
    #
    #

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

    def evaluate(self):
        instances, _ = self.sorted_instances
        active_instances = set()
        for instance in instances:
            if instance.evaluate():
                active_instances.add(instance)
        for instance in instances:
            instance.evaluated = False
        return active_instances

    def stop(self):
        for instance in self.nodes.values():
            instance.stop()
