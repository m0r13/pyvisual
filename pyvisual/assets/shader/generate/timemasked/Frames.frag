#include <generate/timemasked/base.frag>

uniform float uCount;
uniform float uFrameSize; // {"default" : 1.0}
uniform float uAspectCorrection; // {"default" : 0.0}
uniform int uInsideOut; // {"default" : 0}

uniform int uMode; // {"default" : 0, "choices" : ["square frames", "inside-out square frames", "round frames"]}

void generateFrag() {
    vec2 uv = (pyvisualUV - vec2(0.5)) * 2.0;
    uv.x *= mix(1.0, pyvisualResolution.x / pyvisualResolution.y, uAspectCorrection);

    float dist;
    if (uMode == 0) {
        dist = max(abs(uv.x), abs(uv.y));
    } else if (uMode == 1) {
        dist = min(abs(uv.x), abs(uv.y));
    } else if (uMode == 2) {
        dist = length(uv);
    }

    float modValue = 1.0 / uCount;
    float v = modValue - mod(dist, modValue);
    float value = v < uFrameSize * modValue * 0.5 ? 1.0 : 0.0;

    float softness = 0.005;
    float edge = uFrameSize * modValue * 0.5;
    float softValue = 1.0 - smoothstep(edge-softness*0.5, edge+softness*0.5, v);
    softValue *= smoothstep(0.0, softness, v);

    pyvisualOutColor = vec4(vec3(softValue), 1.0);
}

