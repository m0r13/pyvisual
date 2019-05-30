#include <filter/basefilter.frag>

#include <lib/hsv.glsl>

vec4 filterFrag(vec2 uv, vec4 frag) {
    vec3 rgb = hsv2rgb(vec3(frag.r, 1.0, 1.0));

    return vec4(rgb, frag.a);
}

