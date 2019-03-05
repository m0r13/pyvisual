import random

def values_with_softness(base_values):
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

class CheckerboardMeta:
    presets = [
        ("vertical stripes", values_with_softness({
            "uCountX" : 3.5,
            "uCountY" : 0.0,
            "uCenter" : 0
        })),
        ("horizontal stripes", values_with_softness({
            "uCountX" : 0.0,
            "uCountY" : 2.5,
            "uCenter" : 0
        })),
        ("16:9 almost square", values_with_softness({
            "uCountX" : 2.5,
            "uCountY" : 1.5,
            "uCenter" : 0
        })),
        ("4 centered rects + a bit", values_with_softness({
            "uCountX" : 1.8,
            "uCountY" : 1.43,
            "uCenter" : 1
        }))
    ]

class FramesMeta:
    presets = [
        ("square frame blah", values_with_softness({
            "uCount" : 1.97,
            "uFrameSize" : 1.0,
            "uAspectCorrection" : 0.0,
            "uMode" : 0,
            "uInvert" : lambda node: random.randint(0, 1)
        })),
        ("square frame variations", values_with_softness({
            "uCount" : 1.95,
            "uFrameSize" : 1.11,
            "uAspectCorrection" : 0.5,
            "uMode" : lambda node: random.randint(0, 1),
            "uInvert" : lambda node: random.randint(0, 1)
        })),
        ("center circle + ring", values_with_softness({
            "uCount" : 0.91,
            "uFrameSize" : 1.46,
            "uAspectCorrection" : 1.0,
            "uMode" : 2,
            "uInvert" : lambda node: random.randint(0, 1)
        })),
    ]
