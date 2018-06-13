import numpy as np
from glumpy import glm
import var

def apply_transform(transform, matrix=None):
    if matrix is None:
        matrix = np.eye(4, dtype=np.float32)

    if callable(transform):
        return transform(matrix)

    assert type(transform) == list
    for t in transform:
        matrix = t(matrix)
    return matrix

def scale(x, y=None, z=None):
    y = y if y is not None else x
    z = z if z is not None else x
    def _scale(model):
        glm.scale(model, float(x), float(y), float(z))
        return model
    return _scale
