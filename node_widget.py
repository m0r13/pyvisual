import node_meta
import imgui

class ImGuiValue(node_meta.ValueHolder):
    def __init__(self):
        self.label = ""

        self._has_value = True
        self._has_changed = False
        # TODO initial value
        self._value = 0.0

    def show_checkbox(self):
        clicked, self._has_value = imgui.checkbox("", self._has_value)

    def show(self, port_type):
        # TODO
        #if port_type == 0: # input
        #    # TODO str id
        #    imgui.push_id(100)
        #    self.show_checkbox()
        #    imgui.pop_id()
        #    imgui.same_line()
        #    imgui.push_id(101)
        #    self.show_widget()
        #    imgui.pop_id()
        #else:
        #    imgui.push_id(101)
        #    self.show_widget()
        #    imgui.pop_id()
        #    imgui.same_line()
        #    imgui.push_id(100)
        #    self.show_checkbox()
        #    imgui.pop_id()
        self.show_widget()

    @property
    def has_value(self):
        return self._has_value

    @property
    def has_changed(self):
        return self._has_changed

    @property
    def value(self):
        return self._value

    @staticmethod
    def create(port_spec):
        if port_spec["dtype"] == "float":
            return ImGuiFloat()

class ImGuiFloat(ImGuiValue):
    def show_widget(self):
        imgui.push_item_width(50)
        self._has_changed, self._value = imgui.input_float(self.label, self._value)
