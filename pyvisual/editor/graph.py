
class NodeGraphListener:
    def created_node(self, node, ui_data):
        pass

    def removed_node(self, node):
        pass

    def created_connection(node0, port0_id, node1, port1_id):
        pass

    def removed_connection(node0, port0_id, node1, port1_id):
        pass

class NodeGraph:
    def __init__(self):
        self.listeners = []

    #
    # serialization
    #

    def serialize():
        pass

    def unserialize(self, data):
        pass

    #
    # functions for changing node graph
    #

    def create_node(spec, ui_data):
        pass

    def remove_node(node):
        pass

    def set_node_ui_data(self, node, ui_data):
        pass

    def create_connection(node0, port0_id, node1, port1_id):
        pass

    def remove_connection(node0, port0_id, node1, port1_id):
        pass

    # selection management

    #
    #
    #

    @property
    def sorted_instances(self):
        # topological sort
        pass
