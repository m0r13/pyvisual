import numpy as np
from glumpy import glm

def apply_transform(transform, matrix=None):
    if matrix is None:
        matrix = np.eye(4, dtype=np.float32)

    if callable(transform):
        return transform(matrix)

    assert type(transform) == list
    for t in transform:
        matrix = t(matrix)
    return matrix

def translate(x=0.0, y=0.0, z=0.0):
    def _translate(model):
        glm.translate(model, float(x), float(y), float(z))
        return model
    return _translate

def scale(x, y=None, z=None):
    y = y if y is not None else x
    z = z if z is not None else x
    def _scale(model):
        glm.scale(model, float(x), float(y), float(z))
        return model
    return _scale

def zrotate(theta):
    def _zrotate(model):
        glm.zrotate(model, float(theta))
        return model
    return _zrotate
