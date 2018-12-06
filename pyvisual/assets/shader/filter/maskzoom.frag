#include <filter/basefilter.frag>

uniform sampler2D uMask;
uniform float uScale0; // {"default" : 1.0}
uniform float uScale1; // {"default" : 1.0}

vec4 filterFrag(vec2 uv, vec4 frag) {
    float mask = texture2D(uMask, TexCoord0).r;

    vec2 texCoords = uv - vec2(0.5);
    texCoords *= mix(uScale0, uScale1, mask);
    texCoords += vec2(0.5);

    return texture2D(uInputTexture, texCoords);
}

