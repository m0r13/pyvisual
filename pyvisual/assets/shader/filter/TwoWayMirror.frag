#define DONT_SAMPLE_FRAGMENT
#include <filter/basefilter.frag>

#include <lib/transform.glsl>

uniform mat4 uPreTransform;

//uniform bool uMirrorVertical; // {"default" : false}
//uniform bool uMirrorHorizontal; // {"default" : true}

uniform int uMode; // {"choices" : ["none", "vertical", "horizontal"], "default" : 2}

/*
vec4 mirrorFragWith(vec4 frag0, vec2 uv1) {
    vec4 frag1 = texture2D(uInputTexture, uv1);
    vec4 frag = vec4(vec3(0.0), 1.0);
    frag.rgb = frag0.rgb + frag1.rgb;
    return frag;
}
*/

vec4 filterFrag(vec2 uv, vec4 _) {
    vec2 mirroredUV = uv;
    if (uMode == 1) {
        mirroredUV.x = 0.5 - (mirroredUV.x - 0.5);
    } else if (uMode == 2) {
        mirroredUV.y = 0.5 - (mirroredUV.y - 0.5);
    }

    mirroredUV = transformUV(mirroredUV, uPreTransform, textureSize(uInputTexture, 0));

    vec4 frag0 = texture2D(uInputTexture, uv);
    vec4 frag1 = texture2D(uInputTexture, mirroredUV);

    vec4 frag = vec4(vec3(0.0), 1.0);
    frag.rgb = frag0.rgb + frag1.rgb;

    return frag;
}

