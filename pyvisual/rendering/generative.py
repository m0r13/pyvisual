
import numpy as np
import time
import random
import logging
from glumpy import app, gl, glm, gloo, data
from pyvisual.rendering import stage, util

log = logging.getLogger(__name__)

class GenerativeStage(stage.BaseStage):
    _instances = []

    def __init__(self):
        self._evaluated = False
        self._actual_stage = None

        GenerativeStage._instances.append(self)

    @property
    def is_first_evaluation(self):
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
    def reset_instances():
        for instance in GenerativeStage._instances:
            _ = instance.actual_stage
            instance._evaluated = False

class Transitioned(GenerativeStage):
    def __init__(self, generator, transition_config=("common/passthrough.vert", "transition/move.frag", {}, 0.5)):
        super().__init__()

        self._event = generator._event
        self._generator = generator
        self._source = None

        self._old_transition_config = None
        self._transition_config = transition_config
        # actual config is loaded with first transition
        self._transition = stage.TransitionStage("common/passthrough.vert", "common/passthrough.frag")


    def evaluate(self):
        if not self._event.value:
            if self._transition.is_over or self.is_first_evaluation:
                # no transition is running
                # remember current stage as source for next transition
                self._source = self._generator.actual_stage
                #print("old source:", self._source)
                return self._generator
            # don't change current transition/generator
            return None
        else:
            config = self._transition_config
            vertex, fragment, uniforms, duration = config(self._event) if callable(config) else config
            self._transition.set_quad(vertex, fragment, uniforms)
            self._transition.animate_from_to(self._source, self._generator.actual_stage, float(duration))
            return self._transition

class Iterated(GenerativeStage):
    def __init__(self, event, stages, shuffle=False):
        super().__init__()
        
        self._event = event
        self._stages = stages
        self._index = 0
        self._shuffle = shuffle

    def evaluate(self):
        # keep old stage if not triggered
        if not self._event.value and not self.is_first_evaluation:
            return None

        if self._shuffle:
            assert len(self._stages) >= 2
            self._index = self._index + np.random.randint(low=1, high=len(self._stages))
        else:
            self._index += 1
        self._index = self._index % len(self._stages)

        actual_stage = self._stages[self._index]
        if callable(actual_stage):
            actual_stage = actual_stage()
        return actual_stage

class Selected(GenerativeStage):
    def __init__(self, event, stages, min_n=1, max_n=1):
        super().__init__()
        
        self._event = event
        self._stages = stages
        self._min_n = min_n
        if self._min_n > len(self._stages):
            log.warn("Selected stage %s: Min number larger than count of supplied stages. Capping min number.")
            self._min_n = len(self._stages)
        self._max_n = max_n
        if self._max_n > len(self._stages):
            log.warn("Selected stage %s: Max number larger than count of supplied stages. Capping max number.")
            self._max_n = len(self._stages)

    def evaluate(self):
        if not self._event.value and not self.is_first_evaluation:
            return None
        # this selection includes initial state (self.is_first_evaluation)

        k = np.random.randint(low=self._min_n, high=self._max_n + 1)
        indices = set(random.sample(list(range(0, len(self._stages))), k=k))

        stages = []
        for i in indices:
            actual_stage = self._stages[i]
            if callable(actual_stage):
                actual_stage = actual_stage()
            stages.append(actual_stage)

        return stage.Pipeline(stages)

def load_resources(wildcard, **stage_kwargs):
    actual_stages = []
    actual_index = 0
    for i in range(2):
        actual_stages.append(stage.TextureStage(**stage_kwargs))

    stages = []
    for name in util.glob_textures(wildcard):
        def _stage(*args, name=name):
            nonlocal actual_index
            i = actual_index
            actual_stages[i]._texture = util.load_texture(name)
            actual_index = (actual_index + 1) % 2
            return actual_stages[i]
        stages.append(_stage)
    return stages

