#include <filter/basefilter.frag>

uniform float uRedThreshold; // {"default" : 0.5}
uniform float uRedSmoothness; // {"default" : 0.5}

vec4 filterFrag(vec2 uv, vec4 frag) {
    frag.rb = smoothstep(uRedThreshold - uRedSmoothness*0.5, uRedThreshold + uRedSmoothness*0.5, frag.rb);
    return frag;
}
