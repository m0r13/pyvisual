#include <filter/basefilter.frag>

uniform sampler2D uOtherMask;
uniform float uFactor1; // {"default" : 1.0}
uniform float uFactor2; // {"default" : 1.0}

vec4 filterFrag(vec2 uv, vec4 frag) {
    float v1 = frag.r;
    float v2 = texture2D(uOtherMask, uv).r;
    return vec4(vec3(v1 * uFactor1 + v2 * uFactor2), 1.0);
}
