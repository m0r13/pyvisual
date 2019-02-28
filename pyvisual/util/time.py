import math
import time

class PausableTimer:
    def __init__(self, initial_time=0.0):
        self.initial_time_offset = initial_time
        self.time_offset = 0.0

        self._paused = False
        self._paused_time = 0.0
        self._internal_offset = 0.0

    def time(self):
        if self._paused:
            return self._paused_time + self.time_offset
        return time.time() + self.initial_time_offset + self.time_offset + self._internal_offset

    @property
    def paused(self):
        return self._paused

    @paused.setter
    def paused(self, paused):
        if paused == self._paused:
            return

        if paused:
            self._paused_time = self.time() - self.time_offset
        else:
            self._internal_offset = -(time.time() - self._paused_time)
        self._paused = paused

global_time = PausableTimer()

# TODO what kind of interface should timers actually have?
def ScalableTimer():
    _last_time = global_time.time()
    _time = 0.0
    def _timer(scale, reset=False):
        if math.isnan(scale):
            return 0
        nonlocal _last_time, _time
        t = global_time.time()
        if reset:
            _time = 0.0
        dt = t - _last_time
        _time += dt * scale
        _last_time = t
        return _time
    return _timer

