#define DONT_SAMPLE_FRAGMENT
#include <filter/basefilter.frag>

uniform int uMode; // {"default" : 1, "choices" : ["passthrough", "1", "2", "3"]}

vec4 filterFrag(vec2 uv, vec4 frag) {
    vec2 texCoords = uv;

    // uMode == 0 is just passthrough
    if (uMode == 1) {
        //texCoords.x = abs(texCoords.x - 0.5);
        if (texCoords.x > 0.5) {
            texCoords.x = 0.5 - (texCoords.x - 0.5);
        }
    } else if (uMode == 2) {
        //texCoords.y = abs(texCoords.y - 0.5);
        if (texCoords.y > 0.5) {
            texCoords.y = 0.5 - (texCoords.y - 0.5);
        }
    } else if (uMode == 3) {
        //texCoords.x = abs(texCoords.x - 0.5);
        //texCoords.y = abs(texCoords.y - 0.5);
        if (texCoords.x > 0.5) {
            texCoords.x = 0.5 - (texCoords.x - 0.5);
        }
        if (texCoords.y > 0.5) {
            texCoords.y = 0.5 - (texCoords.y - 0.5);
        }
    }

    return texture2D(uInputTexture, texCoords);
}

