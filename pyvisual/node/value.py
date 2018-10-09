from pyvisual.node.base import Node

class InputValue(Node):
    class Meta:
        outputs = [
            {"name" : "output", "dtype" : "float", "show_label" : False}
        ]
        options = {
            "category" : "input",
            "show_title" : False
        }

class OutputValue(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : "float", "show_label" : False}
        ]
        options = {
            "category" : "output",
            "show_title" : False
        }

