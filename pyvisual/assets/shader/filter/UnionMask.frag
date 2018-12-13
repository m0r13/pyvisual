#include <filter/basefilter.frag>

uniform sampler2D uOtherMask;

vec4 filterFrag(vec2 uv, vec4 frag) {
    float v1 = frag.r;
    float v2 = texture2D(uOtherMask, uv).r;
    return vec4(vec3(v1+v2), 1.0);
}
