#include <filter/basefilter.frag>

// preprocessor bool dInvertAlpha; {"default" : false, "group" : "additional"}

vec4 filterFrag(vec2 uv, vec4 frag) {
#if dInvertAlpha
    return vec4(vec3(1.0) - frag.rgb, 1.0 - frag.a);
#else
    return vec4(vec3(1.0) - frag.rgb, frag.a);
#endif
}
