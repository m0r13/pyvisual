from pyvisual.node.base import Node
from pyvisual.node import dtype
from pyvisual.node.io.audio import AudioData, FFTData, DEFAULT_SAMPLE_RATE
from glumpy import gloo
from scipy import interpolate
import numpy as np

RESAMPLE_INTERPOLATIONS = ["nearest", "linear", "quadratic", "cubic"]

class ResampleSSBO(Node):
    class Meta:
        inputs = [
            {"name" : "enabled", "dtype" : dtype.bool, "dtype_args" : {"default" : True}},
            {"name" : "ssbo", "dtype" : dtype.ssbo},
            {"name" : "size", "dtype" : dtype.int, "dtype_args" : {"default" : 256, "range" : [0, float("inf")]}},
            {"name" : "interpolation", "dtype" : dtype.int, "dtype_args" : {"default" : 1, "choices" : RESAMPLE_INTERPOLATIONS}},
        ]
        outputs = [
            {"name" : "ssbo", "dtype" : dtype.ssbo},
        ]

    def __init__(self):
        super().__init__()

        self._ssbo = None

    def _evaluate(self):
        ssbo = self.get("ssbo")
        if ssbo is None:
            self.set("ssbo", None)
            return

        size = int(self.get("size"))
        if size < 2 or not self.get("enabled"):
            self.set("ssbo", ssbo)
            return

        if self._ssbo is None or size != len(self._ssbo):
            self._ssbo = np.zeros((size,), dtype=np.float32).view(gloo.ShaderStorageBuffer)

        interpolation = int(self.get("interpolation"))
        interpolation = max(0, min(len(RESAMPLE_INTERPOLATIONS) - 1, interpolation))
        interpolation = RESAMPLE_INTERPOLATIONS[interpolation]

        x0 = np.linspace(0.0, 1.0, num=len(ssbo))
        x1 = np.linspace(0.0, 1.0, num=size)
        self._ssbo[:] = interpolate.interp1d(x0, ssbo, kind=interpolation)(x1)
        self.set("ssbo", self._ssbo)

class AddSSBO(Node):
    class Meta:
        inputs = [
            {"name" : "ssbo1", "dtype" : dtype.ssbo},
            {"name" : "factor1", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0, "range" : [0.0, float("inf")]}},
            {"name" : "ssbo2", "dtype" : dtype.ssbo},
            {"name" : "factor2", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0, "range" : [0.0, float("inf")]}},
        ]
        outputs = [
            {"name" : "ssbo", "dtype" : dtype.ssbo},
        ]

    def __init__(self):
        super().__init__()

        self._ssbo = None

    def _evaluate(self):
        ssbo1 = self.get("ssbo1")
        ssbo2 = self.get("ssbo2")

        if ssbo1 is None or ssbo2 is None:
            self.set("ssbo", None)
            return

        if len(ssbo1) != len(ssbo2):
            self.set("ssbo", None)
            return

        if self._ssbo is None or len(self._ssbo) != len(ssbo1):
            self._ssbo = np.zeros((len(ssbo1),), dtype=np.float32).view(gloo.ShaderStorageBuffer)
        self._ssbo[:] = self.get("factor1") * ssbo1 + self.get("factor2") * ssbo2
        self.set("ssbo", self._ssbo)

