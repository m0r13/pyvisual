#include <filter/basefilter.frag>

// preprocessor bool dExcludeBackground; // {"default" : false, "group" : "additional"}

uniform sampler2D uMask;
uniform vec2 uTranslate0;
uniform vec2 uTranslate1;

vec4 filterFrag(vec2 uv, vec4 frag) {
    vec2 mask = texture2D(uMask, TexCoord0).gb;

    vec2 texCoords = uv + mix(uTranslate0, uTranslate1, mask);
#if dExcludeBackground
    // exclude background of mask
    if (length(mask.xy) < 0.1) {
        return vec4(vec3(0.0), 1.0);
    }
#endif

    return texture2D(uInputTexture, texCoords);
}

