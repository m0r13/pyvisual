import time
import math
from pyvisual.node.base import Node
from pyvisual.node import dtype

class LFO(Node):
    class Meta:
        inputs = [
            # TODO generator type
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float, "show_label" : False}
        ]
        options = {
            "category" : "generate",
            "show_title" : False
        }

    def evaluate(self):
        value = (math.sin(time.time()) + 1.0) / 2.0
        self.set("output", value)

