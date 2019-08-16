#include <filter/basefilter.frag>

uniform int uCount; // {"default" : 4, "range" : [1, Infinity]}
uniform float uIndex; // {"default" : 0, "range" : [0, Infinity]}
uniform int uMode; // {"choices" : ["single-on", "sweep-in", "sweep-out"], "default" : 0}
uniform bool uInvert; // {"default" : false}

vec4 filterFrag(vec2 uv, vec4 frag) {
    if (frag.a < 0.5) {
        return vec4(vec3(0.0), 1.0);
    }

    int i = int(ceil(frag.r * uCount - 0.01));

    bool on = false;
    float d = 0.0;
    if (uMode == 0) {
        on = int(i) == int(uIndex);
        d = float(abs(int(i) - int(uIndex)));
    } else if (uMode == 1) {
        on = i <= int(uIndex);
        d = max(float(i - uIndex), 0.0);
    } else if (uMode == 2) {
        on = i >= int(uIndex);
        d = max(float(uIndex - i), 0.0);
    }

    float value = d > 0.0 ? 0.0 : 1.0;
    //float value = 1.0 - smoothstep(0.0, 1.5, d);
    if (uInvert) {
        value = 1.0 - value;
    }

    return vec4(vec3(value), 1.0);
}
