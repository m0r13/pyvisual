#include <filter/basefilter.frag>

uniform sampler2D uOtherTexture;

vec4 filterFrag(vec2 uv, vec4 frag) {
    vec4 otherFrag = texture2D(uOtherTexture, uv);

    vec4 result;
    //result.rgb = mix(frag.rgb, otherFrag.rgb, otherFrag.a);
    //result.a = max(frag.a * otherFrag.a, otherFrag.a);
    
    result.rgb = frag.rgb + otherFrag.rgb;
    result.a = frag.a;
    return result;
}
