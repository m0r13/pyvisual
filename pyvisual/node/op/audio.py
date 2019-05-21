from pyvisual.node.base import Node
from pyvisual.node import dtype
from pyvisual.node.io.audio import AudioData, FFTData, DEFAULT_SAMPLE_RATE
from pyvisual.node.op.module import StaticModule
from pyvisual.audio import util
from scipy import signal
from glumpy import gloo
import math
import time
import numpy as np
import imgui
import librosa

AUDIO_FILTER_TYPES = ["low", "high"]
class AudioFilter(Node):
    class Meta:
        inputs = [
            {"name" : "enabled", "dtype" : dtype.bool, "dtype_args" : {"default" : True}},
            {"name" : "input", "dtype" : dtype.audio},
            {"name" : "type", "dtype" : dtype.int, "dtype_args" : {"choices" : AUDIO_FILTER_TYPES}},
            {"name" : "order", "dtype" : dtype.int, "dtype_args" : {"default" : 5, "range" : [1, 10]}},
            {"name" : "cutoff", "dtype" : dtype.float, "dtype_args" : {"default" : 1000.0, "range" : [0.0001, float("inf")]}}
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.audio}
        ]
        options = {
            "category" : "audio"
        }

    def __init__(self):
        super().__init__()

        self.filter = None
        # contains error message if there is a problem
        self.filter_status = None
        self.output = None

    def build_filter(self, sample_rate):
        filter_type = int(self.get("type"))
        if not filter_type in (0, 1):
            filter_type = 0
        btype = AUDIO_FILTER_TYPES[filter_type]
        order = self.get("order")
        cutoff = self.get("cutoff")
        try:
            self.filter = util.Filter(signal.butter, order, cutoff, sample_rate, {"btype" : btype, "analog" : False})
            self.filter_status = None
        except ValueError as e:
            self.filter = None
            self.filter_status = str(e)
            self.filter_status += "\n"
            self.filter_status += "\nFilter type: %s" % btype
            self.filter_status += "\nOrder: %f" % order
            self.filter_status += "\nCutoff: %f" % cutoff
            self.filter_status += "\nSamplerate: %f" % sample_rate

    def _evaluate(self):
        input_audio = self.get("input")

        if input_audio is None:
            self.set("output", None)
            return

        if ((self.filter is None or self.output is None) and self.filter_status is None) \
                or self.have_inputs_changed("type", "order", "cutoff") \
                or self.output.sample_rate != input_audio.sample_rate \
                or self._last_evaluated == 0.0:
            self.build_filter(sample_rate=input_audio.sample_rate)
            self.output = AudioData(input_audio.sample_rate, input_audio.block_size)

        if self.filter is None:
            self.set("output", None)
            return

        if not self.get("enabled"):
            self.set("output", input_audio)
            return

        self.output.clear()
        for block in input_audio.blocks:
            self.output.append(self.filter.process(block))
        self.set("output", self.output)

    def _show_custom_ui(self):
        if self.filter_status is not None:
            imgui.dummy(1, 5)
            imgui.text_colored("Filter error. (?)", 1.0, 0.0, 0.0)
            if imgui.is_item_hovered():
                imgui.set_tooltip(self.filter_status)

    def _show_custom_context(self):
        if imgui.button("copy filter coefficients"):
            if self.filter is not None:
                import clipboard
                clipboard.copy("""a = %s\nb = %s""" % (str(self.filter._a.tolist()), str(self.filter._b.tolist())))

class AbsAudio(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.audio}
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.audio},
        ]
        options = {
            "category" : "audio"
        }

    def _evaluate(self):
        input_audio = self.get("input")
        if input_audio is None:
            self.set("output", None)
            return

        output = AudioData(input_audio.sample_rate, input_audio.block_size)
        for block in input_audio.blocks:
            output.append(np.abs(block))
        self.set("output", output)

class SampleAudio(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.audio}
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float},
        ]
        options = {
            "category" : "audio"
        }

    def _evaluate(self):
        input_audio = self.get("input")
        if input_audio is None:
            self.set("output", 0.0)
            return

        if len(input_audio.blocks) == 0:
            return

        block = input_audio.blocks[-1]
        self.set("output", block[-1])

def create_gauss_kernel(count, sigma):
    # gauss kernel, flipped, normalized, in rows
    kernel = 1.0 / (np.sqrt(2*math.pi) * sigma) * np.exp(- np.arange(0, count)**2 / (2*sigma**2))
    kernel = np.flip(kernel)
    kernel = kernel / kernel.sum()
    return kernel[:, np.newaxis]

class SampleAudioSSBO(Node):
    class Meta:
        inputs = [
            {"name" : "enabled", "dtype" : dtype.bool, "dtype_args" : {"default" : True}},
            {"name" : "input", "dtype" : dtype.audio},
            {"name" : "size", "dtype" : dtype.int, "dtype_args": {"default" : 1024, "range" : [1, float("inf")]}},
            {"name" : "smooth_count", "dtype" : dtype.int, "dtype_args" : {"range" : [1, float("inf")], "default" : 8}},
            {"name" : "smooth_sigma", "dtype" : dtype.float, "dtype_args" : {"default" : 1, "range" : [0.0001, float("inf")]}},
            {"name" : "tune_frequency", "dtype" : dtype.float, "dtype_args" : {"default" : 50, "range" : [0.0001, float("inf")]}},
            {"name" : "scale", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0}},
            {"name" : "smooth_to_zero", "dtype": dtype.bool, "dtype_args" : {"default" : False}},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.ssbo},
        ]

    def __init__(self):
        super().__init__()

        # global sample index where sample of first block starts
        self._blocks_index = 0
        self._blocks = []

        self._last_samples_size = None
        self._last_samples = []
        self._last_samples_kernel = None
        self._ssbo = None

    def _update_ssbo(self, size):
        self._ssbo = np.zeros((size,), dtype=np.float32).view(gloo.ShaderStorageBuffer)

    def _evaluate(self):
        size = self.get_input("size")
        if size.has_changed() or self._ssbo is None:
            self._update_ssbo(int(size.value))

        input_audio = self.get("input")
        if input_audio is None or len(input_audio.blocks) == 0:
            return
        self._blocks.extend(input_audio.blocks)

        # number of samples to be sampled
        c = size.value
        # if samples are always taken from the same index mod some value for a frequency
        # then that frequency always appear with the same phase
        index_mod = input_audio.sample_rate / self.get("tune_frequency") * 4

        total_length = lambda: sum([ len(b) for b in self._blocks ])
        # remove excess blocks, s.t. there are max. index_mod + c samples
        # (index_mod + c should ensure that we can always get c samples starting from some index_mod offset)
        while total_length() - input_audio.block_size > index_mod + c:
            block = self._blocks.pop(0)
            self._blocks_index += len(block)

        last_index = self._blocks_index + total_length()
        # i is index relative to current blocks
        # (and it's the first possible index where (i mod index_mod) == 0)
        i = round(index_mod * math.ceil(self._blocks_index / index_mod)) - self._blocks_index
        assert i >= 0
        # it might happen that there are not enough samples yet
        if i + c >= total_length():
            return

        # TODO perhaps performance improvement, but it's okay for now
        all_samples = np.concatenate(self._blocks)
        samples = all_samples[i:i+int(c)]
        # clear last samples if sample size has changed
        if len(samples) != self._last_samples_size:
            self._last_samples_size = len(samples)
            self._last_samples = []

        # take samples if enabled, otherwise do smoothing by repeating current samples + gauss kernel
        if self.get("enabled") or len(self._last_samples) == 0:
            self._last_samples.append(samples)
        else:
            if self.get("smooth_to_zero"):
                self._last_samples.append(np.zeros_like(self._last_samples[-1]))
            else:
                self._last_samples.append(self._last_samples[-1])
        self._last_samples_size = len(self._last_samples[0])

        smooth_count = int(self.get("smooth_count"))
        smooth_sigma = self.get("smooth_sigma")
        if self.have_inputs_changed("smooth_count", "smooth_sigma") \
                or self._last_samples_kernel is None \
                or len(self._last_samples_kernel) != smooth_count:
            self._last_samples_kernel = create_gauss_kernel(smooth_count, smooth_sigma)

        # have exactly smooth_count of sample sets ready
        while len(self._last_samples) > smooth_count:
            self._last_samples.pop(0)
        if len(self._last_samples) < smooth_count:
            return

        # smooth samples by applying gauss kernel over last sample sets
        samples = np.sum(self._last_samples * self._last_samples_kernel, axis=0)

        self._ssbo[:] = samples * self.get("scale")
        self.set("output", self._ssbo)

class VUNormalizer(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.float},
            {"name" : "offset", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "beat_on", "dtype" : dtype.bool},
            {"name" : "min", "dtype" : dtype.float, "dtype_args" : {"default" : 0.5}},
            {"name" : "max", "dtype" : dtype.float, "dtype_args" : {"default" : 0.9}},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.float}
        ]

    def __init__(self):
        super().__init__()

        self._factor = 1.0

        self._current_max_vu = 0.0
        self._last_vus = []
        self._last_vu_count = 4

    def evaluate(self):
        beat_on = self.get("beat_on")
        vu_norm = (self.get("input") - self.get("offset")) * self._factor
        self.set("output", vu_norm)

        min_vu = self.get("min")
        max_vu = self.get("max")

        # get highest (normalized) vu while beat is on
        if beat_on:
            if self._current_max_vu is None:
                self._current_max_vu = 0.0
            self._current_max_vu = max(self._current_max_vu, vu_norm)

        # once beat turns off...
        if not beat_on and self._current_max_vu is not None:
            self._last_vus.append(self._current_max_vu)
            if len(self._last_vus) >= self._last_vu_count:
                average_vu = sum(self._last_vus) / len(self._last_vus)
                if (average_vu < min_vu or average_vu > max_vu) and average_vu != 0.0:
                    adjust_factor = ((max_vu + min_vu) / 2) / average_vu
                    self._factor *= adjust_factor
                self._last_vus = []
            self._current_max_vu = None

        return vu_norm

def sliding_window_average(n=4):
    window = []
    def _process(value):
        nonlocal window
        window.append(value)
        if len(window) > n:
            window.pop(0)
        return sum(window) / len(window)
    return _process

class BeatAnalyzer(Node):
    class Meta:
        inputs = [
            {"name" : "beat_on", "dtype" : dtype.bool},
        ]
        outputs = [
            {"name" : "beat_running", "dtype" : dtype.bool},
            {"name" : "bpm", "dtype" : dtype.float},
        ]

    def __init__(self):
        super().__init__(always_evaluate=True)

        self.last_beat_on = False

        self.current_bpm = 0.0
        self.is_beat_running = False

        self.last_beat = time.time()
        self.delta_to_last_beat = lambda self=self: time.time() - self.last_beat
        self.bpm_from_last_beat = lambda self=self: 60.0 / self.delta_to_last_beat()

        self.bpm_window_average = sliding_window_average(8)
        self.p = False

    # TODO the whole checking when the beat is running if the
    # bpm with the new beat is within range of current bpm is broken

    # is_beat_running = ...
    def bpm_fits_lower_threshold(self, bpm):
        if not self.is_beat_running or True:
            return bpm > 60.0
        return bpm > self.current_bpm * 0.8
    def bpm_fits_higher_threshold(self, bpm):
        if not self.is_beat_running or True:
            return bpm < 200.0
        return bpm < self.current_bpm * 1.2
    def is_bpm_sensible(self, bpm):
        return self.bpm_fits_lower_threshold(bpm) and self.bpm_fits_higher_threshold(bpm)

    def _evaluate(self):
        beat_on = self.get("beat_on")
        beat_rising = beat_on and not self.last_beat_on
        beat_falling = not beat_on and self.last_beat_on

        if beat_rising:
            bpm = self.bpm_from_last_beat()
            if self.is_bpm_sensible(bpm):
                self.current_bpm = self.bpm_window_average(bpm)
                print("--- bpm", bpm, self.current_bpm, "---")
            else:
                print("hmm, new bpm doesn't make sense:", bpm,)
            self.last_beat = time.time()

        #print(self.bpm_from_last_beat())
        self.is_beat_running = self.bpm_fits_lower_threshold(self.bpm_from_last_beat())
        #print(self.is_beat_running)
        if not self.is_beat_running and not self.p:
            self.bpm_window_average = sliding_window_average(8)
            print("-- emptying avg bpm window --")
            self.p = True
        if self.is_beat_running:
            self.p = False

        self.last_beat_on = beat_on

        self.set("beat_running", self.is_beat_running)
        self.set("bpm", self.current_bpm)

class BeatDetection(StaticModule):
    class Meta:
        pass

    def __init__(self):
        super().__init__("BeatDetection.json")

WINDOW_NAMES = ["hamming", "hanning", "cosine"]
WINDOW_FN = [np.hamming, np.hanning, signal.cosine]

class FFT(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.audio},
            {"name" : "smooth_count", "dtype" : dtype.int, "dtype_args" : {"range" : [4, float("inf")], "default" : 8}},
            {"name" : "smooth_sigma", "dtype" : dtype.float, "dtype_args" : {"default" : 1, "range" : [0.0001, float("inf")]}},
            {"name" : "window", "dtype" : dtype.int, "dtype_args" : {"choices" : WINDOW_NAMES}},
            {"name" : "scale_db", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0, "range" : [0.0, 1.0]}},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.fft},
        ]

    def __init__(self):
        super().__init__()

        self._blocks = []
        self._sample_rate = None
        self._block_size = None
        
        self._fft_len = None
        self._last_magnitudes = []
        self._last_magnitudes_size = None
        self._last_magnitudes_kernel = None

    def _process_fft(self, blocks, samplerate):
        # smoothing here works similar as in SampleAudioSSBO

        samples = np.concatenate(blocks)
        M = len(samples)
        window = WINDOW_FN[int(self.get("window"))](M)
        samples = samples * window

        smooth_count = int(self.get("smooth_count"))
        smooth_sigma = self.get("smooth_sigma")

        Fs = samplerate
        magnitudes = np.abs(np.fft.fft(samples, axis=0)[:M // 2 + 1:-1])

        if len(magnitudes) != self._last_magnitudes_size:
            self._last_magnitudes_size = len(magnitudes)
            self._last_magnitudes = []
        self._last_magnitudes.append(magnitudes)

        # update gauss kernel if smooth count/sigma changed
        if self.have_inputs_changed("smooth_count", "smooth_sigma") \
                or self._fft_len is None or self._fft_len != len(magnitudes) \
                or len(self._last_magnitudes_kernel) != smooth_count:
            self._last_magnitudes_kernel = create_gauss_kernel(smooth_count, smooth_sigma)

        while len(self._last_magnitudes) > smooth_count:
            self._last_magnitudes.pop(0)
        if len(self._last_magnitudes) < smooth_count:
            return

        last_magnitudes = np.array(self._last_magnitudes)
        magnitudes = np.sum(last_magnitudes * self._last_magnitudes_kernel, axis=0)

        scale_db = self.get("scale_db")
        if self.get("scale_db"):
            magnitudes = 20*np.log10(magnitudes)

        frequencies = np.arange(0, len(magnitudes)) * Fs / M
        fft = FFTData(magnitudes, frequencies, frequencies[1])
        self.set("output", fft)

    def _evaluate(self):
        input_audio = self.get("input")
        if input_audio is None:
            self.set("output", None)
            return

        #print("Got %d blocks" % len(input_audio.blocks))
        # TODO expose this!
        N = 4
        overlap = N - 1
        for block in input_audio.blocks:
            self._blocks.append(block)
        self._sample_rate = input_audio.sample_rate
        self._block_size = input_audio.block_size

        generated_fft = False
        while len(self._blocks) >= N:
            fft_blocks = self._blocks[:N]
            process = True

            #to_pop = N - overlap
            #remaining = len(self._blocks) - to_pop
            #assert remaining >= 0
            #if remaining >= N:
            #    process = False

            for i in range(N):
                self._blocks.pop(0)

            #if process or True:
            self._process_fft(fft_blocks, input_audio.sample_rate)
            generated_fft = True
            #else:
            #    pass

        # add current fft value to last fft results for smoothing
        if not generated_fft and len(self._last_magnitudes) != 0:
            self._last_magnitudes.append(self._last_magnitudes[-1])

    def _show_custom_context(self):
        imgui.text("FFT's per frame: ~%.2f" % (self._sample_rate / self._block_size / 60.0))
        imgui.text("Smoothing kernel: %s" % str(", ".join([ "%.3f" % f for f in self._last_magnitudes_kernel ])))

        super()._show_custom_context()

class BandpassFFT(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.fft},
            {"name" : "min", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "max", "dtype" : dtype.float, "dtype_args" : {"default" : 22050.0}},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.fft}
        ]

    def _evaluate(self):
        fft = self.get("input")
        if fft is None:
            self.set("output", None)
            return

        min_freq, max_freq = self.get("min"), self.get("max")

        mask = (fft.frequencies > min_freq) & (fft.frequencies <= max_freq)
        new_fft = FFTData(fft.magnitudes[mask], fft.frequencies[mask], fft.bin_resolution)
        if len(new_fft.frequencies) == 0:
            new_fft = None
        self.set("output", new_fft)

class AWeightingFFT(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.fft},
            {"name" : "alpha", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0, "range": [0.0, 1.0]}},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.fft}
        ]

    def _evaluate(self):
        fft = self.get("input")
        if fft is None:
            self.set("output", None)
            return

        weighting = librosa.A_weighting(fft.frequencies + fft.bin_resolution * 0.5)

        new_fft = fft.copy()
        new_fft.magnitudes *= 10**(self.get("alpha") * weighting / 10.0)
        # for db it would be like this:
        #new_fft.magnitudes += weighting
        self.set("output", new_fft)

class QuantizeFFT(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.fft},
            {"name" : "count", "dtype" : dtype.int, "dtype_args" : {"default" : 10, "range" : [1, float("inf")]}},
            {"name" : "gamma", "dtype" : dtype.float, "dtype_args" : {"default" : 1, "range" : [0.5001, float("inf")]}},
            {"name" : "min_freq", "dtype" : dtype.float, "dtype_args" : {"default" : 0.0}},
            {"name" : "max_freq", "dtype" : dtype.float, "dtype_args" : {"default" : 22100.0}},
            {"name" : "db", "dtype" : dtype.bool, "dtype_args" : {"default" : False}},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.fft}
        ]

    def __init__(self):
        super().__init__()

        self._freqs = []

    def _evaluate(self):
        fft = self.get("input")
        if fft is None:
            self.set("output", None)
            return

        count = int(self.get("count"))
        count = max(0, count)
        gamma = self.get("gamma")

        min_freq, max_freq = self.get("min_freq"), self.get("max_freq")

        mask = (fft.frequencies > min_freq) & (fft.frequencies <= max_freq)
        filtered_fft = FFTData(fft.magnitudes[mask], fft.frequencies[mask], fft.bin_resolution)

        magnitudes = np.zeros((count,), dtype=np.float32)
        frequencies = np.zeros((count,), dtype=np.float32)

        self._freqs = []
        # take count of already filtered fft!
        factor = len(filtered_fft.magnitudes) / count
        for i in range(count):
            # https://dlbeer.co.nz/articles/fftvis.html for gamma formula
            first_index = int(((i / count) ** (1 / gamma)) * len(filtered_fft.magnitudes))
            last_index = int((((i+1) / count) ** (1 / gamma)) * len(filtered_fft.magnitudes))
            magnitudes[i] = filtered_fft.magnitudes[first_index:last_index].mean()
            frequencies[i] = filtered_fft.frequencies[last_index - 1]
            self._freqs.append((i, first_index, last_index, frequencies[i]))

        if self.get("db"):
            magnitudes = 20*np.log10(magnitudes)

        # one peak normalization
        #magnitudes = magnitudes * 1.0 / (np.nanmax(magnitudes) + 0.01)

        filtered_fft = FFTData(magnitudes, frequencies, fft.bin_resolution)
        self.set("output", filtered_fft)

    def _show_custom_context(self):
        for freq in self._freqs:
            imgui.text(str(freq))

        super()._show_custom_context()

class FFT2SSBO(Node):
    class Meta:
        inputs = [
            {"name" : "input", "dtype" : dtype.fft},
            {"name" : "scale", "dtype" : dtype.float, "dtype_args" : {"default" : 1.0, "range" : [0.00001, float("inf")]}},
        ]
        outputs = [
            {"name" : "output", "dtype" : dtype.ssbo},
        ]

    def __init__(self):
        super().__init__()

        self._buffer = None

    def _evaluate(self):
        fft = self.get("input")
        if fft is None:
            self.set("output", None)
            return

        fft_len = len(fft.frequencies)
        if self._buffer is None or fft_len != len(self._buffer):
            self._buffer = np.zeros((fft_len,), dtype=np.float32).view(gloo.buffer.ShaderStorageBuffer)

        self._buffer[:] = fft.magnitudes * self.get("scale")
        self.set("output", self._buffer)

#class ChromaFeaturesFFT(Node):
#    class Meta:
#        inputs = [
#            {"name" : "input", "dtype" : dtype.fft},
#        ]
#        outputs = [
#            {"name" : "test", "dtype" : dtype.float}
#        ]
#
#    def __init__(self):
#        super().__init__()
#
#        #self.test = open("test.dat", "w")
#
#    def _evaluate(self):
#        fft = self.get("input")
#        if fft is None:
#            self.set("test", 0.0)
#            return
#
#        S = np.expand_dims(fft.magnitudes, 1)
#        chroma = librosa.feature.chroma_stft(S=S, sr=22050)
#
#        test = chroma[:, 0].tolist()
#        #self.test.write(" ".join(map(str, test)) + "\n")

#class SpectralCentroidFFT(Node):
#    class Meta:
#        inputs = [
#            {"name" : "input", "dtype" : dtype.fft},
#        ]
#        outputs = [
#            {"name" : "output", "dtype" : dtype.float}
#        ]
#
#    def _evaluate(self):
#        fft = self.get("input")
#        if fft is None:
#            self.set("output", 0.0)
#            return
#
#        rel_frequencies = np.linspace(0, 1, len(fft.frequencies))
#        normalized_magnitudes = fft.magnitudes / sum(fft.magnitudes)
#        spectral_centroid = sum(normalized_magnitudes * rel_frequencies)
#        self.set("output", spectral_centroid)

#class EnergyFFT(Node):
#    class Meta:
#        inputs = [
#            {"name" : "input", "dtype" : dtype.fft}
#        ]
#        outputs = [
#            {"name" : "output", "dtype" : dtype.float}
#        ]
#
#    def _evaluate(self):
#        fft = self.get("input")
#        if fft is None:
#            self.set("output", 0.0)
#            return
#
#        energy = np.sum(fft.magnitudes * fft.magnitudes) / len(fft.magnitudes)
#        self.set("output", energy)

#class ExportFFT(Node):
#    class Meta:
#        inputs = [
#            {"name" : "input", "dtype" : dtype.fft}
#        ]
#
#    def _evaluate(self):
#        fft = self.get("input")
#        if fft is None:
#            return
#
#        fft.magnitudes.tofile("fft.dat")
