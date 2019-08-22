#include <filter/basefilter.frag>

#include <lib/hsv.glsl>

uniform float uHueOffset; // {"default" : 0.0}
uniform float uRedThreshold; // {"default" : 0.5}
uniform float uRedSmoothness; // {"default" : 0.5}

vec4 filterFrag(vec2 uv, vec4 frag) {
    vec3 hsv = rgb2hsv(frag.rgb);
    hsv.r += uHueOffset;
    frag.rgb = hsv2rgb(hsv);

    frag.rgb = smoothstep(uRedThreshold - uRedSmoothness*0.5, uRedThreshold + uRedSmoothness*0.5, frag.rgb);
    return frag;
}
