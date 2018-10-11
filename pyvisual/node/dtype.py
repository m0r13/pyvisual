import collections
import numpy as np

Type = collections.namedtuple("DType", ["name", "base_type", "default"])

bool = Type("bool", "float", lambda: 0.0)
event = Type("event", "float", lambda: 0.0)
int = Type("int", "float", lambda: 0.0)
float = Type("float", "float", lambda: 0.0)
color = Type("color", "vec4", lambda: np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32))
tex2d = Type("tex2d", "tex2d", lambda: None)

