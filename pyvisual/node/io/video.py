import ctypes
import os
import random
import random
import subprocess
import threading
import time

import cv2
import imgui
import numpy as np
from PIL import Image
from glumpy import gloo, gl, glm, app

from pyvisual import assets, util
from pyvisual.node import dtype
from pyvisual.node.base import Node

USE_PBO_TRANSFER = True
PBO_COUNT = 4

class VideoThread(threading.Thread):
    def __init__(self, video_path=""):
        super().__init__()

        self._video_path = video_path
        self._video_path_changed = True
        self._video = None
        self._fps = 30.0
        self._duration = 0.0
        self._is_stream = False

        self._clock = app.clock.Clock()

        self._running = True
        self._play = False
        self._loop = True
        self._speed = None
        self._speed_multiplier = None
        self._seek_time = None

        # read one frame even though video is paused
        self._force_read = True
        # it can happen that video doesn't finish, but reading last frame returns an error
        # remember that to signalize that video is over
        self._frame_grabbed = True

        # initially set by _update_video
        self.frame = None
        self.frame_changed = False

        self.speed = 1.0

    @property
    def video_path(self):
        return self._video_path
    @video_path.setter
    def video_path(self, video_path):
        self._video_path = video_path
        self._video_path_changed = True

    @property
    def has_video_loaded(self):
        return self._video is not None

    @property
    def play(self):
        return self._play
    @play.setter
    def play(self, play):
        self._play = play
        self._force_read = True

    @property
    def loop(self):
        return self._loop
    @loop.setter
    def loop(self, loop):
        self._loop = loop

    @property
    def speed(self):
        return self._speed
    @speed.setter
    def speed(self, speed):
        multiplier = 1
        while abs(speed) >= 2.0:
            speed = speed / 2.0
            multiplier *= 2

        clock_fps = abs(self._fps * speed)
        if abs(speed) < 0.0001:
            self._force_read = True
            clock_fps = 30.0

        self._speed = speed
        self._speed_multiplier = multiplier
        self._clock.set_fps_limit(clock_fps)

    @property
    def time(self):
        if self._video is not None:
            return self._video.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        return 0.0

    @time.setter
    def time(self, seek_time):
        self._seek_time = seek_time

    @property
    def is_over(self):
        if not self._frame_grabbed:
            return True
        if self._speed < 0.0:
            return self.time == 0.0
        return self.time >= self.duration

    @property
    def duration(self):
        return self._duration

    def _update_video(self):
        self._video = None
        self._video_path_changed = False
        self._is_stream = False

        self._fps = 30.0
        self._duration = 1.0

        path = self._video_path
        is_local_path = not path.startswith("http://")
        if is_local_path:
            path = os.path.join(assets.ASSET_PATH, self._video_path or "")
        if not self._video_path or (is_local_path and not os.path.exists(path)):
            self.frame = np.zeros((1, 1, 4), dtype=np.uint8)
            self.frame_changed = True
            if not USE_PBO_TRANSFER:
                self.frame = self.frame.view(gloo.Texture2D)
            return

        self._video = cv2.VideoCapture(path)
        self._force_read = True

        width = int(self._video.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self._video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_count  = int(self._video.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = self._video.get(cv2.CAP_PROP_FPS)

        self._fps = fps
        self._duration = max(0.0, (frame_count - 1) / fps)
        self._is_stream = not is_local_path
        self.frame = np.zeros((height, width, 4), dtype=np.uint8)
        self.frame_changed = True
        if not USE_PBO_TRANSFER:
            self.frame = self.frame.view(gloo.Texture2D)

    def run(self):
        self._update_video()

        while self._running:
            dt = self._clock.tick()

            if self._video_path_changed:
                self._update_video()
            if self._video is None:
                continue

            # seek time before looping to handle reverse playing and saved time correctly
            if self._seek_time is not None:
                seek_time = max(0, min(self._seek_time, self._duration))
                self._video.set(cv2.CAP_PROP_POS_MSEC, seek_time * 1000.0)
                self._seek_time = None
                self._force_read = True
            if not self._is_stream and self.is_over and self.loop:
                if self._speed > 0.0:
                    self.time = 0.0
                else:
                    self.time = self.duration
            # respect global time for playback, pause video too (but we don't care about time offset)
            if (not self._play or abs(self._speed) < 0.001 or util.time.global_time.paused) and not self._force_read:
                continue
            self._force_read = False

            grabbed, frame = self._video.read()

            # if we're playing reverse: go two frames back
            # two frames because we just read one and want to go another frame back
            step_size = self._speed_multiplier
            if self._speed < 0.0:
                index = int(self._video.get(cv2.CAP_PROP_POS_FRAMES))
                self._video.set(cv2.CAP_PROP_POS_FRAMES, index - 1 - step_size)
            elif self._speed_multiplier > 1:
                index = int(self._video.get(cv2.CAP_PROP_POS_FRAMES))
                self._video.set(cv2.CAP_PROP_POS_FRAMES, index + step_size - 1)

            # remember if there was a problem grabbing the frame
            # seems to happen sometimes with last frame(s) of a video
            if not grabbed:
                self._frame_grabbed = False
                continue
            self._frame_grabbed = True

            frame_rgba = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
            self.frame[:, :, :] = frame_rgba
            self.frame_changed = True

    def stop(self):
        self._running = False

class PlayVideo(Node):

    USES_OPENGL = True

    class Meta:
        inputs = [
            {"name" : "video", "dtype" : dtype.assetpath, "dtype_args" : {"prefix" : "video"}},
            {"name" : "loop", "dtype" : dtype.bool, "dtype_args" : {"default" : True}},
            {"name" : "play", "dtype" : dtype.bool, "dtype_args" : {"default" : True}},
            {"name" : "speed", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "rel_seek_time", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "rel_seek", "dtype" : dtype.event},
            {"name" : "abs_seek_time", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "abs_seek", "dtype" : dtype.event},
            {"name" : "random_seek", "dtype" : dtype.event},
        ]
        outputs = [
            {"name" : "frame", "dtype" : dtype.tex2d},
            {"name" : "is_over", "dtype" : dtype.bool},
            {"name" : "time", "dtype" : dtype.float},
            {"name" : "duration", "dtype" : dtype.float},
        ]
        initial_state = {
            "time" : 0.0
        }
        random_state = {
            "time" : lambda node: random.random() * 100000.0
        }

    def __init__(self):
        # construct it already here to be able to set time with set_state
        self._video_thread = VideoThread()

        super().__init__(always_evaluate=True)

        self._video_thread.start()

        self._pbo_shape = None
        self._pbo_index = 0
        self._pbos = None

        self._frame = None

    def _transfer_frame_pbo(self):
        # generate PBO's 
        if self._video_thread.has_video_loaded and (self._pbo_shape != self._video_thread.frame.shape):
            if self._pbos is not None:
                gl.glDeleteBuffers(PBO_COUNT, self._pbos)

            self._pbo_shape = self._video_thread.frame.shape
            self._pbos = gl.glGenBuffers(PBO_COUNT)

            h, w, b = self._pbo_shape
            num_bytes = h*w*b
            for pbo in self._pbos:
                gl.glBindBuffer(gl.GL_PIXEL_UNPACK_BUFFER, pbo)
                gl.glBufferData(gl.GL_PIXEL_UNPACK_BUFFER, num_bytes, None, gl.GL_STREAM_DRAW)
            gl.glBindBuffer(gl.GL_PIXEL_UNPACK_BUFFER, 0)

        # generate/update OpenGL texture
        if (self._frame is None or self._frame.shape != self._pbo_shape) and self._pbo_shape is not None:
            self._frame = np.zeros(self._pbo_shape, dtype=np.uint8).view(gloo.Texture2D)
            self._frame.activate()
            self._frame.deactivate()

        # do the transfer of pixel data from cpu to gpu using PBO's
        # inspired by this: https://gist.github.com/roxlu/4663550
        if self._video_thread.has_video_loaded and self._video_thread.frame_changed:
            self._video_thread.frame_changed = False

            pbo = self._pbos[self._pbo_index]
            gl.glBindBuffer(gl.GL_PIXEL_UNPACK_BUFFER, pbo)
            t = self._frame._handle
            h, w, b = self._pbo_shape
            assert t != None and t != 0
            gl.glBindTexture(gl.GL_TEXTURE_2D, t)
            gl.glTexSubImage2D(gl.GL_TEXTURE_2D, 0, 0, 0, w, h, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, None)

            h, w, b = self._pbo_shape
            num_bytes = h*w*b

            self._pbo_index = (self._pbo_index + 1) % PBO_COUNT
            pbo = self._pbos[self._pbo_index]
            gl.glBindBuffer(gl.GL_PIXEL_UNPACK_BUFFER, pbo)
            # this might be an alternative, but not so fast as tested so far
            #gl.glBufferSubData(gl.GL_PIXEL_UNPACK_BUFFER, 0, num_bytes, ctypes.c_void_p(self._video_thread.frame.ctypes.data))

            ptr = gl.glMapBuffer(gl.GL_PIXEL_UNPACK_BUFFER, gl.GL_WRITE_ONLY)
            if ptr != 0:
                #start = time.time()
                ctypes.memmove(ctypes.c_voidp(ptr), ctypes.c_void_p(self._video_thread.frame.ctypes.data), num_bytes)
                #end = time.time()
                #elapsed = end - start
                #print("Took %.2fms, %.2fMB/s" % (elapsed * 1000, (num_bytes / 1000000) / elapsed))
                gl.glUnmapBuffer(gl.GL_PIXEL_UNPACK_BUFFER)
            gl.glBindBuffer(gl.GL_PIXEL_UNPACK_BUFFER, 0)

    def _evaluate(self):
        if USE_PBO_TRANSFER:
            self._transfer_frame_pbo()

        video = self.get_input("video")
        if video.has_changed():
            self._video_thread.video_path = video.value

        loop = self.get_input("loop")
        if loop.has_changed():
            self._video_thread.loop = loop.value

        play = self.get_input("play")
        if play.has_changed():
            self._video_thread.play = play.value

        speed = self.get_input("speed")
        if speed.has_changed():
            self._video_thread.speed = speed.value

        # allow seeking only when a video is loaded
        #  (prevent it here because video thread doesn't forbid it
        #  so set_state can set time already before video is loaded)
        if self._video_thread.has_video_loaded:
            if self.get("abs_seek"):
                self._video_thread.time = self.get("abs_seek_time")
            if self.get("rel_seek"):
                duration = self._video_thread.duration
                if duration != 0.0:
                    self._video_thread.time = (self._video_thread.time + self.get("rel_seek_time")) % duration
            if self.get("random_seek"):
                duration = self._video_thread.duration
                time = random.random() * duration
                self._video_thread.time = time

        if USE_PBO_TRANSFER:
            self.set("frame", self._frame)
        else:
            self.set("frame", self._video_thread.frame)
        self.set("is_over", self._video_thread.is_over)
        self.set("time", self._video_thread.time)
        self.set("duration", self._video_thread.duration)

    def stop(self):
        self._video_thread.stop()
        self._video_thread.join()

    def get_state(self):
        return {"time" : self._video_thread.time}

    def set_state(self, state):
        if "time" in state:
            time = state["time"]
            # if a video is loaded, take time modulo duration
            # so we can just generate a arbitrarily large number as random state
            if self._video_thread.has_video_loaded:
                duration = self._video_thread.duration
                time = time % duration
            self._video_thread.time = time

class FFMPEGVideoRecorder(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.tex2d},
            {"name" : "start", "dtype" : dtype.event},
            {"name" : "stop", "dtype" : dtype.event},
        ]
        outputs = [
            {"name" : "recording", "dtype" : dtype.bool},
        ]

    def __init__(self):
        super().__init__(always_evaluate=True)

        self._recording = False
        self._texture_shape = None
        self._process = None

        self._pbo_shape = None
        self._pbo_index = 0
        self._pbos = None

    def _download_texture(self, texture):
        # generate PBO's 
        if self._pbos is None or self._pbo_shape != texture.shape:
            if self._pbos is not None:
                gl.glDeleteBuffers(2, self._pbos)

            self._pbo_shape = texture.shape
            self._pbos = gl.glGenBuffers(2)

            h, w, b = self._pbo_shape
            num_bytes = h*w*b
            for pbo in self._pbos:
                gl.glBindBuffer(gl.GL_PIXEL_PACK_BUFFER, pbo)
                gl.glBufferData(gl.GL_PIXEL_PACK_BUFFER, num_bytes, None, gl.GL_STREAM_DRAW)
            gl.glBindBuffer(gl.GL_PIXEL_PACK_BUFFER, 0)

        # do the transfer of pixel data from gpu to cpu using PBO's
        # inspired by this: https://gist.github.com/roxlu/4663550
        h, w, b = self._pbo_shape
        b -= 1
        num_bytes = h*w*b
        pbo = self._pbos[self._pbo_index]
        gl.glBindBuffer(gl.GL_PIXEL_PACK_BUFFER, pbo)
        t = texture._handle
        assert t != None and t != 0
        gl.glBindTexture(gl.GL_TEXTURE_2D, t)
        gl.glGetTexImage(gl.GL_TEXTURE_2D, 0, gl.GL_RGB, gl.GL_UNSIGNED_BYTE, ctypes.c_void_p(0))

        self._pbo_index = (self._pbo_index + 1) % 2
        pbo = self._pbos[self._pbo_index]
        gl.glBindBuffer(gl.GL_PIXEL_PACK_BUFFER, pbo)
        ptr = gl.glMapBuffer(gl.GL_PIXEL_PACK_BUFFER, gl.GL_READ_ONLY)
        data = None
        if ptr != 0:
            p = ctypes.cast(ptr, ctypes.POINTER(ctypes.c_ubyte * num_bytes))
            data = np.frombuffer(p.contents, dtype=np.uint8).copy().reshape((h, w, b))
            gl.glUnmapBuffer(gl.GL_PIXEL_PACK_BUFFER)
        gl.glBindBuffer(gl.GL_PIXEL_PACK_BUFFER, 0)

        assert data is not None
        return data

    def _start_recording(self):
        path = "test.mp4"

        texture = self.get("input")
        if texture is None:
            return
        self._texture_shape = texture.shape
        h, w, _ = texture.shape

        command = [
            "ffmpeg",
            "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", "%dx%d" % (w, h),
            "-pix_fmt", "rgb24",
            "-r", "30",
            "-i", "-",
            #"-i", "pipe:0",
            #"-c:v", "h264_nvenc", "-preset", "slow", "-profile:v", "high", "-b:v", "5M",
            "-an",
            util.image.generate_screenshot_path(suffix=".mp4"),
        ]

        self._process = subprocess.Popen(command, stdin=subprocess.PIPE, bufsize=-1) #1000000*10)

        self._recording = True

    def _stop_recording(self):
        self._process.stdin.close()

        self._recording = False

    def _evaluate(self):
        if self._recording and self.get("stop"):
            self._stop_recording()
        if not self._recording and self.get("start"):
            self._start_recording()

        if self._recording:
            texture = self.get("input")
            if texture is None or texture.shape != self._texture_shape:
                self._stop_recording()
            else:
                #start = time.time()
                data = self._download_texture(texture)
                #end = time.time()
                #print("Reading stuff takes %.2f ms" % ((end - start) * 1000))
                #start = time.time()
                b = data.tobytes()
                #end = time.time()
                #print("Test takes %.2f ms" % ((end - start) * 1000))
                #start = time.time()
                self._process.stdin.write(b)
                #end = time.time()
                #print("Write takes %.2f ms" % ((end - start) * 1000))

        self.set("recording", self._recording)

    def stop(self):
        if self._recording:
            self._stop_recording()

