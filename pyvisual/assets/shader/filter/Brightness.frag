#include <filter/basefilter.frag>

uniform float uBrightness; // {"default" : 1.0}

vec4 filterFrag(vec2 uv, vec4 frag) {
    return vec4(frag.rgb * uBrightness, frag.a);
}
