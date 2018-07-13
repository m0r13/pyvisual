#!/usr/bin/env python3

import sys
sys.path.append("/home/moritz/dev/misc/glumpy-test")

import numpy as np
import ctypes
import time
import sys
import threading

from pyvisual.audio.pulseaudio import *

class PulseAudioContext(threading.Thread):
    def __init__(self, process_block, sample_rate=5000, block_size=256):
        super().__init__()
        self._mainloop = None
        self._mainloop_api = None
        self._context = None
        self._stream = None

        self._todo = []
        self._todo_index = []

        self._sample_rate = sample_rate
        self._block_size = block_size
        self._process_block = process_block

    def _quit(ret):
        mainloop_api.contents.quit(mainloop_api, ret)

    def _context_state_callback(self, context, userdata):
        state = pa_context_get_state(context)
        if state == PA_CONTEXT_READY:
            print("Connected!")

            sample_spec = pa_sample_spec()
            sample_spec.format = PA_SAMPLE_FLOAT32LE
            sample_spec.rate = self._sample_rate
            sample_spec.channels = 1

            self._stream = pa_stream_new(context, bytes("Test", "ascii"), ctypes.pointer(sample_spec), None)

            def stream_state_callback(stream, userdata):
                self._stream_state_callback(stream, userdata)
            self._stream_state_callback_stub = pa_stream_notify_cb_t(stream_state_callback)
            pa_stream_set_state_callback(self._stream, self._stream_state_callback_stub, None)

            def stream_read_callback(stream, length, userdata):
                self._stream_read_callback(stream, length, userdata)
            self._stream_read_callback_stub = pa_stream_request_cb_t(stream_read_callback)
            pa_stream_set_read_callback(self._stream, self._stream_read_callback_stub, ctypes.c_void_p(0xdeadbeef))

            buffer_attr = pa_buffer_attr()
            buffer_attr.fragsize = 1024
            buffer_attr.maxlength = -1
            pa_stream_connect_record(self._stream, None, ctypes.pointer(buffer_attr), PA_STREAM_ADJUST_LATENCY)

            #quit(0)
        if state == PA_CONTEXT_TERMINATED:
            print("Disconnected!")
        if state == PA_CONTEXT_FAILED:
            print("Unable to connect!")
            self._quit(1)

    def _stream_state_callback(self, stream, userdata):
        print("Stream callback!")
        state = pa_stream_get_state(stream)
        if state == PA_STREAM_CREATING:
            pass
        if state == PA_STREAM_TERMINATED:
            print("Stream terminated!")
        if state == PA_STREAM_READY:
            print("Stream created!")
        if state == PA_STREAM_FAILED:
            print("Unable to create stream", pa_strerror(pa_context_errno(self._context)))
            self._quit(1)

    def _stream_read_callback(self, stream, length, userdata):
        if length == 0:
            # workaround
            #print("state", pa_stream_get_state(stream))
            self._stream_state_callback(self._stream, None)
            return

        def arrays_len(arrays):
            return sum([ array.shape[0] for array in arrays ])

        buf = ctypes.c_void_p()
        length = size_t(0)
        #pa_stream_peek(stream, ctypes.byref(buf), ctypes.byref(length))
        if pa_stream_peek(stream, ctypes.byref(buf), ctypes.byref(length)) < 0:
            print("Unable to read from stream:", pa_strerror(pa_context_errno(context)))
            self._quit(1)
            return
        pa_stream_drop(stream)

        count = length.value // 4
        fragment_ptr = ctypes.cast(buf, ctypes.POINTER(ctypes.c_float))
        fragment = np.array(np.fromiter(fragment_ptr, dtype=np.float32, count=count))

        self._todo.append(fragment)
        self._todo_index.append(0)

        def actual_size():
            if not len(self._todo):
                return 0
            return len(self._todo[0]) - self._todo_index[0] + arrays_len(self._todo[1:])
        while actual_size() >= self._block_size:
            #print("---")
            #print([ len(a) for a in self._todo ], self._todo_index)
            blocks = []
            for array, index in zip(list(self._todo), list(self._todo_index)):
                remaining_needed = self._block_size - arrays_len(blocks)
                assert remaining_needed > 0
                #print(remaining_needed)
                array_part = array[index:min(index+remaining_needed, len(array))]
                left_behind = len(array) - index - len(array_part)
                #print("taking %d of %d (leaving %d)" % (len(array_part), len(array), left_behind))
                blocks.append(array_part)
                if left_behind == 0:
                    self._todo.pop(0)
                    self._todo_index.pop(0)
                else:
                    assert id(array) == id(self._todo[0])
                    self._todo_index[0] = index + len(array_part)
                #print("have now %d" % arrays_len(blocks))
                if len(array_part) == remaining_needed:
                    #print("over!")
                    break

            assert arrays_len(blocks) == self._block_size
            #print("====>", arrays_len(blocks))
            #print(actual_size(), "left over")

            block = np.concatenate(blocks, axis=0)
            #for sample in block[:-1]:
            #    print(sample, -1.0, file=sys.stderr)
            #print(block[-1], 1.0, file=sys.stderr)
            #process_block(block)

            self._process_block(block)
        return None
    
    def run(self):
        self._mainloop = pa_mainloop_new()
        self._mainloop_api = pa_mainloop_get_api(self._mainloop)
        self._context = pa_context_new(self._mainloop_api, bytes("Hello Pulseaudio!", "ascii"))

        def context_state_callback(context, userdata):
            self._context_state_callback(context, userdata)
        self._context_state_callback_stub = pa_context_notify_cb_t(context_state_callback)
        pa_context_set_state_callback(self._context, self._context_state_callback_stub, None)
        pa_context_connect(self._context, None, PA_CONTEXT_NOFLAGS, None)

        pa_mainloop_run(self._mainloop, None)

        pa_context_disconnect(self._context)

        if self._stream:
            pa_xfree(self._stream)
        if context:
            pa_xfree(self._context)
        if mainloop:
            pa_mainloop_free(self._mainloop)

def quit(ret):
    mainloop_api.contents.quit(mainloop_api, ret)

stream = None
def state_callback(context, userdata):
    global stream

    state = pa_context_get_state(context)
    if state == PA_CONTEXT_READY:
        print("Connected!")

        sample_spec = pa_sample_spec()
        sample_spec.format = PA_SAMPLE_FLOAT32E
        sample_spec.rate = self._sample_rate
        sample_spec.channels = 1

        stream = pa_stream_new(context, bytes("Test", "ascii"), ctypes.pointer(sample_spec), None)

        pa_stream_set_state_callback(stream, pa_stream_notify_cb_t(stream_state_callback), None)
        pa_stream_set_read_callback(stream, pa_stream_request_cb_t(stream_read_callback), None)

        buffer_attr = pa_buffer_attr()
        buffer_attr.fragsize = 128
        buffer_attr.maxlength = -1
        pa_stream_connect_record(stream, None, ctypes.pointer(buffer_attr), PA_STREAM_ADJUST_LATENCY)

        #quit(0)
    if state == PA_CONTEXT_TERMINATED:
        print("Disconnected!")
    if state == PA_CONTEXT_FAILED:
        print("Unable to connect!")
        quit(1)

def stream_state_callback(stream, userdata):
    state = pa_stream_get_state(stream)
    if state == PA_STREAM_CREATING:
        pass
    if state == PA_STREAM_TERMINATED:
        print("Stream terminated!")
    if state == PA_STREAM_READY:
        print("Stream created!")
    if state == PA_STREAM_FAILED:
        print("Unable to create stream", pa_strerror(pa_context_errno(context)))
        quit(1)

blocksize = 128
def arrays_len(arrays):
    return sum([ array.shape[0] for array in arrays ])
todo = []
todo_index = []
def stream_read_callback(stream, length, userdata):
    global todo, todo_index

    buf = ctypes.c_void_p()
    length = size_t(0)
    pa_stream_peek(stream, ctypes.byref(buf), ctypes.byref(length))
    #if pa_stream_peek(stream, ctypes.byref(buf), ctypes.byref(length)) < 0:
    #    print("Unable to read from stream:", pa_strerror(pa_context_errno(context)))
    #    quit(1)
    #    return
    pa_stream_drop(stream)
    
    if length.value <= 0:
        return

    count = length.value // 4
    samples = ctypes.cast(buf, ctypes.POINTER(ctypes.c_float))
    #print(samples[0])
    #print([ samples[i] for i in range(count) ])

    mysamples = np.array(np.fromiter(samples, dtype=np.float32, count=count))
    #print(mysamples)

    mysamples = np.array([ samples[i] for i in range(count) ])
    #mysamples = np.array([1, 2, 3])
    #print(mysamples)
    
    #print([ s for s in mysamples ])
    #print(min(mysamples), max(mysamples))
    
    #print("Got a block of %d" % len(mysamples))

    todo.append(mysamples)
    todo_index.append(0)

    def actual_size():
        if not len(todo):
            return 0
        return len(todo[0]) - todo_index[0] + arrays_len(todo[1:])
    while actual_size() >= blocksize:
        #print("---")
        #print([ len(a) for a in todo ], todo_index)
        blocks = []
        for array, index in zip(list(todo), list(todo_index)):
            remaining_needed = blocksize - arrays_len(blocks)
            assert remaining_needed > 0
            #print(remaining_needed)
            array_part = array[index:min(index+remaining_needed, len(array))]
            left_behind = len(array) - index - len(array_part)
            #print("taking %d of %d (leaving %d)" % (len(array_part), len(array), left_behind))
            blocks.append(array_part)
            if left_behind == 0:
                todo.pop(0)
                todo_index.pop(0)
            else:
                assert id(array) == id(todo[0])
                todo_index[0] = index + len(array_part)
            #print("have now %d" % arrays_len(blocks))
            if len(array_part) == remaining_needed:
                #print("over!")
                break

        assert arrays_len(blocks) == blocksize
        #print("====>", arrays_len(blocks))
        print(actual_size(), "left over")

        block = np.concatenate(blocks, axis=0)
        #for sample in block[:-1]:
        #    print(sample, -1.0, file=sys.stderr)
        #print(block[-1], 1.0, file=sys.stderr)
        process_block(block)

    #tp = type(samples)
    #np.ctypeslib.prep_pointer(samples, (count, ))
    #samples = np.array(samples, copy=True)
    #samples = np.ctypeslib.as_array(samples, (count,))
    #print(samples)

    return None

if __name__ == "__main__":
    from scipy import signal
    import util
    import threading

    beat_lowpass = util.Filter(signal.butter, 5, 50, 5000, {"btype" : "low", "analog" : False})
    amplitude_lowpass = util.Filter(signal.butter, 5, 2.5, 5000, {"btype" : "low", "analog" : False})
    def process(block):
        beat = beat_lowpass.process(block)
        amplitude = amplitude_lowpass.process(beat)

    context = PulseAudioContext(process, sample_rate=5000)
    context.start()
    context.join()
