#include <filter/basefilter.frag>

uniform sampler2D uMask;
uniform vec2 uTranslate0;
uniform vec2 uTranslate1;

vec4 filterFrag(vec2 uv, vec4 frag) {
    vec2 mask = texture2D(uMask, TexCoord0).gb;

    vec2 texCoords = uv + mix(uTranslate0, uTranslate1, mask);

    return texture2D(uInputTexture, texCoords);
}

