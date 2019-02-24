#include <filter/basefilter.frag>

vec4 filterFrag(vec2 uv, vec4 frag) {
    return vec4(vec3(1.0) - frag.rgb, frag.a);
}
