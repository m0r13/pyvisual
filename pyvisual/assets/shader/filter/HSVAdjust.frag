#include <filter/basefilter.frag>

uniform float uHue; // {"default" : 0.0}
uniform float uSaturation; // {"default" : 1.0, "range" : [0.0, Infinity]}
uniform float uValue; // {"default" : 1.0, "range" : [0.0, Infinity]}

uniform bool uValueInvert; // {"default" : false}

#include <lib/hsv.glsl>

vec4 filterFrag(vec2 uv, vec4 frag) {
    vec3 hsv = rgb2hsv(frag.rgb);
    hsv.r += uHue;
    hsv.g = clamp(hsv.g * uSaturation, 0.0, 1.0);
    if (uValueInvert) {
        hsv.b = 1.0 - hsv.b;
    }
    hsv.b = clamp(hsv.b * uValue, 0.0, 1.0);
    vec3 rgb = hsv2rgb(hsv);

    return vec4(rgb, frag.a);
}

