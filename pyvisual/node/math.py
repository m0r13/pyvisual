from pyvisual.node.base import Node
import imgui

class AddFloat(Node):
    class Meta:
        inputs = [
            {"name" : "v0", "dtype" : "float", "show_label" : False},
            {"name" : "v1", "dtype" : "float", "show_label" : False}
        ]
        outputs = [
            {"name" : "output", "dtype" : "float", "show_label" : False}
        ]
        options = {
            "category" : "math",
        }

    def evaluate(self):
        self.outputs["output"].value = self.inputs["v0"].value + self.inputs["v1"].value

class FloatLambda(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : "float", "show_label" : False},
        ]
        outputs = [
            {"name" : "output", "dtype" : "float", "show_label" : False}
        ]
        options = {
            "category" : "math",
        }

    def evaluate(self):
        pass

    def show_custom_ui(self):
        imgui.dummy(1, 5)
        imgui.text("Coming soon...")
