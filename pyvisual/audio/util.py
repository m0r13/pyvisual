import sys
import numpy as np
from scipy import signal

def dump_blocks(*blocks, file=sys.stderr):
    for samples in zip(*blocks):
        print(" ".join(map(str, samples)), file=file)

class Filter:
    def __init__(self, filter_type, order, freq, sample_freq, filter_kwargs):
        norm_freq = freq / (sample_freq * 0.5)
        self._b, self._a = filter_type(order, norm_freq, **filter_kwargs)
        self._zf = signal.lfiltic(self._b, self._a, np.array([0.0]))

    def process(self, block):
        out, self._zf = signal.lfilter(self._b, self._a, block, zi=self._zf)
        return out

