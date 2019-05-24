#define DONT_SAMPLE_FRAGMENT

#include <filter/basefilter.frag>

uniform sampler2D uMask;
uniform float uOffset;

vec4 filterFrag(vec2 uv, vec4 _) {
    vec4 mask = texture2D(uMask, uv);
    vec2 normal = (mask.yz - 0.5) * 2.0;

    vec2 size = textureSize(uInputTexture, 0);
    return texture2D(uInputTexture, uv + normal * uOffset / size);
}
