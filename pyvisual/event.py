import numpy as np

from pyvisual.rendering import var

class Event(var.Var):
    _instances = []

    def __init__(self):
        self._value = False
        self._evaluated = False

        Event._instances.append(self)

    def evaluate(self):
        raise NotImplementedError()

    @property
    def value(self):
        if not self._evaluated:
            self._value = self.evaluate()
            self._evaluated = True
        return self._value

    @staticmethod
    def reset_instances():
        for instance in Event._instances:
            _ = instance.value
            instance._evaluated = False

class ExprEvent(Event):
    def __init__(self, expr):
        super().__init__()
        self._expr = expr

    def evaluate(self):
        return self._expr()

class Keys(Event):
    def __init__(self, window):
        super().__init__()

        self._keys = set()

        def on_key_press(code, modifier, self=self):
            self._keys.add((code, modifier))
        window.attach(on_key_press=on_key_press)
        # push one more (empty) handler layer
        # the glumpy app (launched later) seems to overwrite the current layer
        window.attach()

    def evaluate(self):
        keys = self._keys
        self._keys = set()
        return keys

    def __getitem__(self, key):
        if not isinstance(key, tuple):
            if not isinstance(key, int):
                raise TypeError()
            key = (key, 0)
        
        if not isinstance(key, tuple) or not len(key) == 2:
            raise TypeError()
        return ExprEvent(lambda self=self, key=key: key in self.value)

class MultiEvent(Event):
    def __init__(self, event, channels):
        super().__init__()

        self._event = event
        if isinstance(channels, (tuple, list)):
            channels = { channel:1.0 for channel in channels } 
        self._channels = list(channels.keys())
        self._weights = np.array(list(channels.values()))
        self._weights = self._weights / np.sum(self._weights)

    def evaluate(self):
        empty_value = { channel:False for channel in self._channels }
        if not self._event.value:
            return empty_value

        i = np.random.choice(np.arange(len(self._channels)), p=self._weights)
        empty_value[self._channels[i]] = True
        return empty_value

    def __getitem__(self, key):
        if not isinstance(key, str):
            raise TypeError()
        return ExprEvent(lambda self=self, key=key: self.value[key])

class TimerEvent(Event):
    def __init__(self, interval):
        super().__init__()
        self._interval = interval
        self._last = 0

    def evaluate(self):
        if time.time() - self._last  > self._interval:
            self._last = time.time()
            return True
        return False

class EveryOnEvent(Event):
    def __init__(self, event, every_n):
        super().__init__()
        self._event = event
        self._every_n = every_n
        self._index = 0

    def evaluate(self):
        if not self._event.value:
            return False
        if self._index == 0:
            self._index = (self._index + 1) % self._every_n
            return True
        self._index = (self._index + 1) % self._every_n
        return False

