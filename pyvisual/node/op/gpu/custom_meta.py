from pyvisual.node import dtype
import random

# add a button to the node to randomize the preset here
# is handled in Filter / TimeMaskedGenerate node clases
# TODO a bit hacky as code is duplicated
INPUTS = [
    {"name" : "randomize_preset", "dtype" : dtype.event}
]

def checkerboard_values_with_softness(base_values):
    def _generate(node):
        values = dict(base_values)

        choice = random.choice(["none", "none", "none", "soft01", "soft23"])

        def one_of_two():
            return random.choice([[0.2, 0.005], [0.005, 0.2]])

        s0, s1, s2, s3 = {
            "none" : lambda: [0.005, 0.005, 0.005, 0.005],
            "soft01" : lambda: one_of_two() + [0.005, 0.005],
            "soft23" : lambda: [0.005, 0.005] + one_of_two(),
        }[choice]()

        values["uSoftness0"] = s0
        values["uSoftness1"] = s1
        values["uSoftness2"] = s2
        values["uSoftness3"] = s3
        return values
    return _generate

class CheckerboardMeta:
    inputs = INPUTS
    presets = [
        ("vertical stripes", checkerboard_values_with_softness({
            "uCountX" : 3.5,
            "uCountY" : 0.0,
            "uCenter" : 0
        })),
        ("horizontal stripes", checkerboard_values_with_softness({
            "uCountX" : 0.0,
            "uCountY" : 2.5,
            "uCenter" : 0
        })),
        ("16:9 almost square", checkerboard_values_with_softness({
            "uCountX" : 2.5,
            "uCountY" : 1.5,
            "uCenter" : 0
        })),
        ("4 centered rects + a bit", checkerboard_values_with_softness({
            "uCountX" : 1.8,
            "uCountY" : 1.43,
            "uCenter" : 1
        }))
    ]

def frame_values_with_softness(base_values):
    def _generate(node):
        values = dict(base_values)

        choice = random.choice(["none", "none", "none", "soft0", "soft1"])

        s0, s1= {
            "none" : [0.005, 0.005],
            "soft0" : [0.2, 0.005],
            "soft1" : [0.005, 0.2]
        }[choice]

        values["uSoftness0"] = s0
        values["uSoftness1"] = s1
        return values
    return _generate

class FramesMeta:
    inputs = INPUTS
    presets = [
        ("square frame blah", frame_values_with_softness({
            "uCount" : 1.97,
            "uFrameSize" : 1.0,
            "uAspectCorrection" : 0.0,
            "uMode" : 0,
            "uInvert" : lambda node: random.randint(0, 1)
        })),
        ("square frame variations", frame_values_with_softness({
            "uCount" : 1.95,
            "uFrameSize" : 1.11,
            "uAspectCorrection" : 0.5,
            "uMode" : lambda node: random.randint(0, 1),
            "uInvert" : lambda node: random.randint(0, 1)
        })),
        ("center circle + ring", frame_values_with_softness({
            "uCount" : 0.91,
            "uFrameSize" : 1.46,
            "uAspectCorrection" : 1.0,
            "uMode" : 2,
            "uInvert" : lambda node: random.randint(0, 1)
        })),
    ]
