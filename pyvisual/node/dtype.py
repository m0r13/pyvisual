import collections
import numpy as np

DType = collections.namedtuple("DType", ["name", "default"])

int = DType("int", lambda: 0)
float = DType("float", lambda: 0.0)
vec4 = DType("vec4", lambda: np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32))
tex2d = DType("tex2d", lambda: -1)

