#define DONT_SAMPLE_FRAGMENT
#include <filter/basefilter.frag>

#include <lib/transform.glsl>

uniform mat4 uTransform0;
uniform mat4 uTransform1;

vec4 filterFrag(vec2 uv, vec4 frag) {
    // TODO SampleN
    vec2 size = textureSize(uInputTexture, 0);
    vec4 frag0 = texture2D(uInputTexture, transformUV(uv, uTransform0, size));
    vec4 frag1 = texture2D(uInputTexture, transformUV(uv, uTransform1, size));
    // TODO blending mode!
    return mix(frag0, frag1, 0.5);
}

