#define DONT_SAMPLE_FRAGMENT
#include <filter/basefilter.frag>

#include <lib/transform.glsl>

uniform mat4 uPreTransform;
uniform sampler2D uMask;
uniform float uMaskFactor; // {"default" : 1.0, "range" : [0.0, Infinity]}

vec4 filterFrag(vec2 uv, vec4 _) {
    
    vec2 transformedUV = transformUV(uv, uPreTransform, textureSize(uInputTexture, 0));
    vec4 frag = texture2D(uInputTexture, transformedUV);
    frag.a *= texture2D(uMask, uv).r * uMaskFactor;
    return frag;
}
