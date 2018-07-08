#!/usr/bin/env python3

"""
01-lowpass-filters.py - The effect of the order of a filter.

For this first example about filtering, we compare the frequency
spectrum of three common lowpass filters.

- Tone : IIR first-order lowpass
- ButLP : IIR second-order lowpass (Butterworth)
- MoogLP : IIR fourth-order lowpass (+ resonance as an extra parameter)

Complementary highpass filters for the Tone and ButLP objects are Atone
and ButHP. Another common highpass filter is the DCBlock object, which
can be used to remove DC component from an audio signal.

The next example will present bandpass filters.

"""
from pyo import *
import time

device_infos = pa_get_devices_infos()
def device_to_index(name):
    for card, infos in enumerate(device_infos):
        for device, info in infos.items():
            if info["name"] == name:
                return device
    assert False

s = Server(duplex=1)
s.setOutputDevice(device_to_index("pulseout"))
s.setInputDevice(device_to_index("pulsemonitor"))
s = s.boot()

n = Input()

# Common cutoff frequency control
freq = Sig(50)
freq.ctrl([SLMap(10, 5000, "lin", "value", 50)], title="Cutoff Frequency")

# Three different lowpass filters
tone = Tone(n, freq)
butlp = ButLP(n, freq)
mooglp = MoogLP(n, freq)

# Interpolates between input objects to produce a single output
sel = Selector([tone, butlp, mooglp])
sel.ctrl(title="Filter selector (0=Tone, 1=ButLP, 2=MoogLP)")

freq2 = Sig(2.5)
freq2.ctrl([SLMap(1.0, 100, "lin", "value", 2.5)], title="Blah frequency")

# Displays the spectrum contents of the chosen source
sp = Spectrum(sel)

test = ButLP(Abs(sel), freq2)

threshold = Sig(0.15)
threshold.ctrl([SLMap(0.0, 1.0, "lin", "value", 0.15)], title="Beat threshold")

def beat_on():
    print("Beat on!")
trig_on = TrigFunc(Thresh(test, threshold=0.15, dir=1), beat_on)

def beat_off():
    print("Beat off!")
trig_off = TrigFunc(Thresh(test, threshold=0.15, dir=0), beat_off)

mixer = Mixer(outs=1, chnls=2)
mixer.addInput(0, test)
mixer.addInput(1, threshold)
mixer.setAmp(0, 0, 1.0)
mixer.setAmp(1, 1, 1.0)

scope = Scope(mixer[0])
#scope_threshold = Scope(threshold)

s.start()
while True:
    time.sleep(1)
#s.gui(locals())

