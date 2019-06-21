from pyvisual.editor.graph import NodeGraphListener
from pyvisual.node.io.texture import Renderer
from pyvisual.node.io.value import InputXXX

class GraphTraits(NodeGraphListener):
    def __init__(self):
        self._render_nodes = []
        self._input_value_nodes = []

    #
    # general stuff, accessing the different traits
    #

    def add_graph(self, graph):
        graph.add_listener(self)

    @property
    def output_texture(self):
        if len(self._render_nodes) == 0:
            return None
        return self._render_nodes[-1].texture

    @property
    def input_value_nodes(self):
        return self._input_value_nodes

    #
    # graph handlers
    #

    def created_node(self, graph, node, ui_data):
        if isinstance(node, Renderer):
            self._render_nodes.append(node)
        if isinstance(node, InputXXX):
            self._input_value_nodes.append(node)

    def removed_node(self, graph, node):
        if isinstance(node, Renderer):
            self._render_nodes.remove(node)
        if isinstance(node, InputXXX):
            self._input_value_nodes.remove(node)


