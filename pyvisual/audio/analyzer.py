#!/usr/bin/env python3

import logging
import threading
import numpy as np
from scipy import signal, fftpack

from pyvisual import event
from pyvisual.audio import pulse, util
from pyvisual.rendering import var

log = logging.getLogger(__name__)

class RingBuffer:
    def __init__(self, size):
        self._size = size
        self._index = 0
        self._buffer = np.zeros((size, ), dtype=np.float32)

    def append(self, value):
        self._buffer[self._index] = value
        self._index = (self._index + 1) % self._size

    @property
    def size(self):
        return self._size

    @property
    def first(self):
        return self._buffer[self._index:]

    @property
    def second(self):
        return self._buffer[0:self._index]

    @property
    def contents(self):
        return np.concat()

class NormalizedVU(event.Event):
    def __init__(self, vu, beat_status, min_vu=0.5, max_vu=0.9, last_vu_count=4):
        super().__init__()
        self._vu = vu
        self._beat_status = beat_status

        self._min_vu = min_vu
        self._max_vu = max_vu
        self._factor = 1.0

        self._current_max_vu = 0.0
        self._last_vus = []
        self._last_vu_count = last_vu_count

    def evaluate(self):
        vu_norm = self._vu.value * self._factor

        # get highest (normalized) vu while beat is on
        if self._beat_status.value:
            if self._current_max_vu is None:
                self._current_max_vu = 0.0
            self._current_max_vu = max(self._current_max_vu, vu_norm)

        # once beat turns off...
        if not self._beat_status.value and self._current_max_vu is not None:
            self._last_vus.append(self._current_max_vu)
            if len(self._last_vus) >= self._last_vu_count:
                average_vu = sum(self._last_vus) / len(self._last_vus)
                if (average_vu < self._min_vu or average_vu > self._max_vu) and average_vu != 0.0:
                    adjust_factor = ((self._max_vu + self._min_vu) / 2) / average_vu
                    self._factor *= adjust_factor
                self._last_vus = []
            self._current_max_vu = None

        return vu_norm

class AudioAnalyzer:
    EVENT_BEAT_ON = 0
    EVENT_BEAT_OFF = 1
    EVENT_BEAT_STATUS = 2
    EVENT_VU = 3
    EVENT_COUNT = 4

    def __init__(self):
        self._beat_threshold = 0.15
        self._beat_gain = 3.0
        self._beat_values = RingBuffer(30*10)
        self._beat_on = False
        
        self._events = []
        self.beat_on = event.ExprEvent(lambda: self._events[self.EVENT_BEAT_ON])
        self.beat_off = event.ExprEvent(lambda: self._events[self.EVENT_BEAT_OFF])
        self.beat_status = event.ExprEvent(lambda: self._events[self.EVENT_BEAT_STATUS])
        self.vu = event.ExprEvent(lambda: self._events[self.EVENT_VU])
        self.vu_norm = NormalizedVU(self.vu, self.beat_status)

        # 128@5000Hz would correspond to 1100@44100Hz, so should be fine
        # and 5000 / 128 => 39 blocks per second of audio, good for 30 fps video
        self._pulse = pulse.PulseAudioContext(self._process_block, block_size=128, sample_rate=5000)

        self._beat_lowpass = util.Filter(signal.butter, 5, 50, 5000, {"btype" : "low", "analog" : False})
        self._beat_highpass = util.Filter(signal.butter, 5, 5, 5000, {"btype" : "high", "analog" : False})
        self._amplitude_lowpass = util.Filter(signal.butter, 5, 2.5, 5000, {"btype" : "low", "analog" : False})
        self._current_beat_amplitude = 0.0
        self._current_beat_on = False

        #self._current_fft = np.array([0.0, 0.0])

    @property
    def beat_threshold(self):
        return self._beat_threshold
    @beat_threshold.setter
    def beat_threshold(self, beat_threshold):
        self._beat_threshold = beat_threshold

    @property
    def beat_gain(self):
        return self._beat_gain
    @beat_gain.setter
    def beat_gain(self, beat_gain):
        self._beat_gain = beat_gain

    @property
    def beat_values(self):
        return np.concatenate([self._beat_values.first, self._beat_values.second], axis=0) * self._beat_gain

    def _process_block(self, block):
        beat = self._beat_lowpass.process(self._beat_highpass.process(block))
        amplitude = self._amplitude_lowpass.process(np.abs(beat))
        self._current_beat_amplitude = amplitude[-1]
        self._current_beat_on = amplitude[-1] * self._beat_gain >= self._beat_threshold

        #window = signal.blackman(len(block))
        #test = fftpack.fft(block * window)
        #self._current_fft = test

    def process(self):
        #beat_value = self._beat.get(False)
        beat_value = self._current_beat_amplitude
        self._beat_values.append(beat_value)

        #print(self._beat._base_objs[0]._getStream())
        #print(self._beat._base_objs[0]._getStream().getDuration())

        self._events = [False] * self.EVENT_COUNT
        beat_on = self._current_beat_on
        if beat_on and not self._beat_on:
            # beat turning off
            print("beat off")
            self._events[self.EVENT_BEAT_ON] = True
        elif not beat_on and self._beat_on:
            # beat turning on
            print("beat on")
            self._events[self.EVENT_BEAT_OFF] = True
        self._beat_on = beat_on
        self._events[self.EVENT_BEAT_STATUS] = self._beat_on
        self._events[self.EVENT_VU] = beat_value

    def start(self):
        self._pulse.start()

    def stop(self):
        self._pulse.stop()
        self._pulse.join()

if __name__ == "__main__":
    analyzer = AudioAnalyzer()
    analyzer.start()
    analyzer._pulse.join()
