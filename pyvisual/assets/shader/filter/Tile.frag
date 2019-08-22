#define DONT_SAMPLE_FRAGMENT
#include <filter/basefilter.frag>

#include <lib/transform.glsl>

uniform mat4 uPreTransform;
uniform int uCount; // {"default" : 2, "range" : [1, Infinity]}
uniform int uMode; // {"choices" : ["vertical", "horizontal"]}

vec4 filterFrag(vec2 uv, vec4 frag) {
    float size = 1.0 / float(uCount);
    if (uMode == 1) {
        uv = vec2(uv.y, uv.x);
    }
    uv.x = mod(uv.x, size) - 0.5*size;

    // TODO
    // fix transformation here!!!
    uv = transformUV(uv, uPreTransform, textureSize(uInputTexture, 0));
    
    uv.x = 0.5 + uv.x;
    if (uMode == 1) {
        uv = vec2(uv.y, uv.x);
    }

    //return vec4(vec3(uv.x), 1.0);
    return texture2D(uInputTexture, uv);
}
