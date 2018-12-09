#include <filter/basefilter.frag>

uniform float uHue; // {"default" : 0.0}
uniform float uSaturation; // {"default" : 1.0, "range" : [0.0, Infinity]}
uniform float uValue; // {"default" : 1.0, "range" : [0.0, Infinity]}

// From: http://lolengine.net/blog/2013/07/27/rgb-to-hsv-in-glsl

// All components are in the range [0…1], including hue.
vec3 rgb2hsv(vec3 c)
{
    vec4 K = vec4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
    vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));
    vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));

    float d = q.x - min(q.w, q.y);
    float e = 1.0e-10;
    return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);
}

// All components are in the range [0…1], including hue.
vec3 hsv2rgb(vec3 c)
{
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

vec4 filterFrag(vec2 uv, vec4 frag) {
    vec3 hsv = rgb2hsv(frag.rgb);
    hsv.r += uHue;
    hsv.g = clamp(hsv.g * uSaturation, 0.0, 1.0);
    hsv.b = clamp(hsv.b * uValue, 0.0, 1.0);
    vec3 rgb = hsv2rgb(hsv);

    return vec4(rgb, frag.a);
}

