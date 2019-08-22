#include <filter/basefilter.frag>

uniform int uCount; // {"default" : 4, "range" : [2, Infinity]}

vec4 filterFrag(vec2 uv, vec4 frag) {
    frag.rgb = ceil(frag.rgb * uCount) / float(uCount);
    return frag;
}
