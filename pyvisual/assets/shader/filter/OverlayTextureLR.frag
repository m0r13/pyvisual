#include <filter/basefilter.frag>

uniform sampler2D uOtherTexture;
uniform float uFactor0; // {"default" : 1.0}
uniform float uFactor1; // {"default" : 1.0}
uniform float uFactorLeft; // {"default" : 1.0, "range" : [0.0, 1.0]}
uniform float uFactorRight; // {"default" : 1.0, "range" : [0.0, 1.0]}
uniform int uMode; // {"choices" : ["add", "mul", "diff"]}

vec4 filterFrag(vec2 uv, vec4 frag) {
    vec4 otherFrag = texture2D(uOtherTexture, uv);
    otherFrag.rgb *= uv.x < 0.5 ? uFactorLeft : uFactorRight;

    vec4 result;
    // TODO !!
    // for masking compatibility also multiply mask value
    result.a = frag.a * otherFrag.r;
    //result.rgb = mix(frag.rgb, otherFrag.rgb, otherFrag.a);
    //result.a = max(frag.a * otherFrag.a, otherFrag.a);
    

    if (uMode == 0) {
        result.rgb = frag.rgb * uFactor0 + otherFrag.rgb * uFactor1;
    } else if (uMode == 1) {
        result.rgb = frag.rgb * uFactor0 * otherFrag.rgb * uFactor1;
    } else if (uMode == 2) {
        result.rgb = abs(frag.rgb * uFactor0 - otherFrag.rgb * uFactor1);
    }
    
    return result;
}
