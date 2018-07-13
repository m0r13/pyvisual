import numpy as np
import cv2
import threading
from glumpy import app, gl, glm, gloo, data

class Looper:
    def __init__(self, start=None, end=None, bounce=False):
        self._start = start
        self._end = end
        self._bounce = bounce

    def process(self, video):
        start = self._start if self._start is not None else 0.0
        end = self._end if self._end is not None else video.length

        print(video.time, end)
        if video.time >= end:
            if self._bounce:
                video.time = end
                video.mode = not video.mode
            else:
                video.time = start
        if video.time < start:
            if self._bounce:
                video.time = start
                video.mode = not video.mode
            else:
                video.time = end

class ForwardBackward:
    def __init__(self, main_move, main_speed, back_move, back_speed):
        self._main_move = main_move
        self._main_speed = main_speed
        self._back_move = back_move
        self._back_speed = back_speed

        self._main_forward = None
        self._is_main = None
        self._change = None

    def process(self, video):
        def next_time():
            a, b = self._main_move if self._is_main else self._back_move
            return (b - a) * np.random.random() + a
        def next_speed():
            a, b = self._main_speed if self._is_main else self._back_speed
            return (b - a) * np.random.random() + a

        def clamp(timestamp):
            return max(0, min(video.length, timestamp))
        def addtime(delta):
            if video.mode:
                return clamp(video.time + delta)
            return clamp(video.time - delta)

        if self._main_forward is None:
            self._main_forward = video.mode
            self._is_main = True
            self._change = addtime(next_time())
            video.speed = next_speed()

        forward = video.mode
        # check if end of video is reached, then toggle main forward
        if forward and video.time == video.length:
            print("End reached")
            self._main_forward = False
            #self._is_main = not self._is_main
            self._is_main = True
            video.mode = self._main_forward
            video.speed = next_speed()
            self._change = addtime(next_time())
            return
        elif not forward and video.time == 0:
            self._main_forward = True
            #self._is_main = not self._is_main
            self._is_main = True
            video.mode = self._main_forward
            video.speed = next_speed()
            video.speed = next_speed()
            self._change = addtime(next_time())
            return

        # check if end of my loop is reached, then toggle back forward
        if forward and video.time >= self._change:
            self._is_main = not self._is_main
            video.mode = not video.mode
            self._change = addtime(next_time())
        if not forward and video.time <= self._change:
            self._is_main = not self._is_main
            video.mode = not video.mode
            video.speed = next_speed()
            self._change = addtime(next_time())

class VideoPlayer(threading.Thread):

    FORWARD = True
    BACKWARD = False

    def __init__(self, path, time_control=None):
        super(VideoPlayer, self).__init__()

        self._video = cv2.VideoCapture(path)

        self._time_control = time_control
        self._clock = app.clock.Clock()
        self._mode = VideoPlayer.FORWARD
        self._paused = False
        self._paused_read = False

        self._width = int(self._video.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height = int(self._video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._fps = self._video.get(cv2.CAP_PROP_FPS)
        self._current_frame = np.zeros((self._height, self._width, 4), dtype=np.uint8)
        self.speed = 1.0

        self._frame_count = int(self._video.get(cv2.CAP_PROP_FRAME_COUNT))
        if self._frame_count >= 1:
            self._frame_count -= 1

    @property
    def current_frame(self):
        return self._current_frame

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, mode):
        self._mode = mode

    @property
    def paused(self):
        return self._paused
    @paused.setter
    def paused(self, paused):
        if not self.paused and paused:
            self._paused_read = False
        self._paused = paused

    @property
    def speed(self):
        return self._speed
    @speed.setter
    def speed(self, speed):
        self._speed = speed
        self._clock.set_fps_limit(self._fps * self._speed)

    @property
    def time(self):
        return self._frame_index / self._fps
    @time.setter
    def time(self, timestamp):
        self._paused_read = False
        self._frame_index = int(timestamp * self._fps)

    @property
    def length(self):
        return self._frame_count / self._fps

    @property
    def _frame_index(self):
        return int(self._video.get(cv2.CAP_PROP_POS_FRAMES))
    @_frame_index.setter
    def _frame_index(self, index):
        self._video.set(cv2.CAP_PROP_POS_FRAMES, max(0, min(self._frame_count - 1, int(index))))

    def run(self):
        while True:
            self._clock.tick()
            if self._time_control:
                self._time_control.process(self)
            if self.paused and self._paused_read:
                continue
            grabbed, frame = self._video.read()
            self._paused_read = True
            if self.mode == VideoPlayer.BACKWARD:
                self._frame_index = self._frame_index - 2

            if not grabbed:
                continue

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_rgba = np.insert(frame_rgb, 3, 255, axis=2)
            self._current_frame = frame_rgba

