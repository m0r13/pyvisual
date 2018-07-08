#!/usr/bin/env python3

import numpy as np
import time
import random
from PIL import Image
from glumpy import app, gl, glm, gloo, data, key
from glumpy.ext import glfw
from rendering import stage, transform, video, var, util

app.use("glfw")
window = app.Window()

class GenerativeStage(stage.BaseStage):
    _instances = []

    def __init__(self):
        self._evaluated = False
        self._actual_stage = None

        GenerativeStage._instances.append(self)

    @property
    def first_evaluation(self):
        return self._actual_stage is None

    def evaluate(self):
        raise NotImplementedError()

    @property
    def actual_stage(self):
        if not self._evaluated:
            stage = self.evaluate()
            # keep actual stage when evaluate doesn't return anything
            if stage is not None:
                self._actual_stage = stage
            self._evaluated = True
        assert self._actual_stage is not None, "%s needs an actual stage set" % repr(self)
        return self._actual_stage

    def render_texture(self, texture):
        return self.actual_stage.render_texture(texture)

    def render_screen(self, texture, target_size):
        self.actual_stage.render_screen(texture, target_size)

    @staticmethod
    def reset_stages():
        for stage in GenerativeStage._instances:
            _ = stage.actual_stage
            stage._evaluated = False

class Event:
    _events = []

    def __init__(self):
        Event._events.append(self)

        self._value = False
        self._evaluated = False

    def evaluate(self):
        raise NotImplementedError()

    @property
    def value(self):
        if not self._evaluated:
            self._value = self.evaluate()
            self._evaluated = True
        return self._value

    def apply(self, expr):
        return ExprEvent(expr)

    def __and__(self, other):
        return self.apply(lambda self=self, other=other: self.value and other.value)

    def __or__(self, other):
        return self.apply(lambda self=self, other=other: self.value or other.value)

    def __invert__(self):
        return self.apply(lambda self=self: not self.value)

    @staticmethod
    def reset_events():
        for event in Event._events:
            _ = event.value
            event._evaluated = False

class ExprEvent(Event):
    def __init__(self, expr):
        super().__init__()
        self._expr = expr

    def evaluate(self):
        return self._expr()

class Keys(Event):
    def __init__(self):
        super().__init__()
        self._keys = set()

    def attach(self, window):
        def on_key_press(code, modifier, self=self):
            self._keys.add((code, modifier))
        window.attach(on_key_press=on_key_press)

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

# Beat(On|Off)Trigger

# Advanced
# EveryN(trigger=BeatOnTrigger(), n=3)
# And(trigger1, trigger2), Or(trigger1, trigger2)
#   trigger1.is_active and trigger2.is_active
# Multichannel trigger (randomly trigger event 1, 2, 3...)
# triggers per timestep, and lazy evaluation (would play well with composition of triggers)

# GenerativeStage
#    self.actual_stage
# but how to generate that?
# Transition(trigger, generator)
#   every time that trigger triggers...
#   if trigger: transition.animate_to(generator.actual_stage)
#   notes
#     - give actual stage to transition
#     - create new transition object every time?

class Transitioned(GenerativeStage):
    def __init__(self, generator, transition_config=("common/passthrough.vert", "transition/move.frag", {})):
        super().__init__()

        self._event = generator._event
        self._generator = generator
        self._transition = stage.TransitionStage("common/passthrough.vert", "transition/move.frag")
        self._old_transition_config = None
        self._transition_config = transition_config

        self._source = None

    def evaluate(self):
        if not self._event.value:
            if self._transition.is_over or self.first_evaluation:
                # no transition is running
                # remember current stage as source for next transition
                self._transition.source = self._generator.actual_stage
                self._source = self._generator.actual_stage
                #print("old source:", self._source)
                return self._generator
            # don't change current transition/generator
            return None
        else:
            #self._transition.animate_to(self._generator, 1.0)
            
            #self._transition.animate_from_to(self._transition.source, self._generator, 1.0)

            config = self._transition_config
            vertex, fragment, uniforms = config(self._event) if callable(config) else config
            self._transition.set_quad(vertex, fragment, uniforms)
            self._transition.animate_from_to(self._source, self._generator.actual_stage, 0.7)
            return self._transition

class Iterated(GenerativeStage):
    def __init__(self, event, stages, shuffle=False):
        super().__init__()

        self._event = event
        self._stages = stages
        self._index = 0
        self._shuffle = shuffle

    def evaluate(self):
        if self.first_evaluation:
            return self._stages[self._index]
        # keep old stage if not value
        if not self._event.value:
            return None

        if self._shuffle:
            assert len(self._stages) >= 2
            self._index = self._index + np.random.randint(low=1, high=len(self._stages))
        else:
            self._index += 1
        self._index = self._index % len(self._stages)

        return self._stages[self._index]

# NOutOfM
class NOutOf(GenerativeStage):
    def __init__(self, event, stages, min_n, max_n):
        super().__init__()

        self._event = event
        self._stages = stages
        self._min_n = min_n
        self._max_n = max_n

    def evaluate(self):
        if not self._event.value and not self.first_evaluation:
            return None

        k = np.random.randint(low=self._min_n, high=self._max_n + 1)
        indices = set(random.sample(list(range(0, len(self._stages))), k=k))

        stages = []
        for i in indices:
            stages.append(self._stages[i])

        return stage.Pipeline(stages)

keys = Keys()
timer = TimerEvent(1.0)

test = EveryOnEvent(timer, 2)
test = test | keys[(glfw.GLFW_KEY_A, 0)]
test = MultiEvent(test, ["a", "b"])

@window.event
def on_draw(dt):
    app.clock.tick()
    window.clear()

    w, h = window.get_size()
    pipeline.render_screen(None, (w, h))

    #print(keys.value)
    #print(test.value)
    #print(test["a"].value)

    Event.reset_events()
    GenerativeStage.reset_stages()

@window.event
def on_key_press(symbol, modifiers):
    # q
    if symbol == 81:
        window.close()

@window.event
def on_resize(width, height):
    pass

@window.event
def on_init():
    app.clock.set_fps_limit(30)

    keys.attach(window)

none = ExprEvent(lambda: False)
key_space = keys[key.SPACE]
key_right = keys[key.RIGHT]

def transition(*args):
    vertex = "common/passthrough.vert"
    fragment = None
    if key_right.value:
        fragment = "transition/move.frag"
        uniforms = {}
    if key_space.value:
        fragment = "transition/test.frag"
        uniforms = {"strength" : 0.2}
    return vertex, fragment, uniforms

pipeline = stage.Pipeline()
pipeline.add_stage(Transitioned(Iterated(key_right | key_space, [
    stage.TextureStage(util.load_texture(name)) for name in util.glob_textures("vapor/*")

], shuffle=True), transition))
#pipeline.add_stage(NOutOf(none, stages=[
#    stage.ShaderStage("common/passthrough.vert", "common/inv.frag"),
#    stage.ShaderStage("common/passthrough.vert", "common/passthrough.frag"),
#], min_n=1, max_n=1))
app.run()
