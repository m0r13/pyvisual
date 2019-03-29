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
        self._zf = signal.lfilter_zi(self._b, self._a)
        self._first_block = True

    def process(self, block):
        if self._first_block:
            self._first_block = False
            self._zf = self._zf * block[0]
        out, self._zf = signal.lfilter(self._b, self._a, block, zi=self._zf)
        return out

