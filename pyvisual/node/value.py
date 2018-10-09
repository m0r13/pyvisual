from pyvisual.node.base import Node

class InputFloat(Node):
    class Meta:
        outputs = [
            {"name" : "output", "dtype" : "float", "show_label" : False}
        ]
        options = {
            "category" : "input",
            "show_title" : False
        }

class OutputFloat(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : "float", "show_label" : False}
        ]
        options = {
            "category" : "output",
            "show_title" : False
        }

class InputColor(Node):
    class Meta:
        outputs = [
            {"name" : "output", "dtype" : "vec4", "show_label" : False},
        ]
        options = {
            "category" : "input",
#            "show_title" : False
        }

class OutputColor(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : "vec4", "show_label" : False},
        ]
        options = {
            "category" : "output",
#            "show_title" : False
        }

