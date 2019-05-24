#include <filter/basefilter.frag>

uniform float uCount; // {"default" : 8.0}
uniform float uGamma; // {"default" : 0.8}

vec4 filterFrag(vec2 uv, vec4 frag) {
    frag.rgb = pow(frag.rgb, vec3(uGamma));
    frag.rgb = floor(frag.rgb * uCount) / uCount;
    frag.rgb = pow(frag.rgb, vec3(1.0 / uGamma));
    return frag;
}
