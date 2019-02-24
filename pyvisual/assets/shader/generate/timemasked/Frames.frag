#include <generate/timemasked/base.frag>

uniform float uCount;
uniform float uFrameSize; // {"default" : 1.0}
uniform int uAspectCorrect; // {"default" : 0}
uniform int uInsideOut; // {"default" : 0}

void generateFrag() {
    vec2 uv = (pyvisualUV - vec2(0.5)) * 2.0;
    if (uAspectCorrect > 0) {
        uv.x *= pyvisualResolution.x / pyvisualResolution.y;
    }

    float dist;
    if (uInsideOut > 0) {
        dist = min(abs(uv.x), abs(uv.y));
    } else {
        dist = max(abs(uv.x), abs(uv.y));
    }

    float modValue = 1.0 / uCount;
    float value = modValue - mod(dist, modValue) < uFrameSize * modValue * 0.5 ? 1.0 : 0.0;

    pyvisualOutColor = vec4(vec3(value), 1.0);
}

