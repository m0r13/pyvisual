#define DONT_SAMPLE_FRAGMENT
#include <filter/basefilter.frag>

uniform int uMode; // {"default" : 1, "choices" : ["passthrough", "1", "2", "3", "4", "5"]}
// only for modes 4 and 5
uniform float uDoubleCenter; // {"default" : 0.2, "range" : [0.0, 0.5]}

vec4 filterFrag(vec2 uv, vec4 frag) {
    vec2 texCoords = uv;

    // uMode == 0 is just passthrough
    if (uMode == 1) {
        //texCoords.x = abs(texCoords.x - 0.5);
        //texCoords.x = 0.5;
        
        // THIS WAS A HACK
        /*
        if ((texCoords.x > 0.5 && uCenterSwitch == 0) || (texCoords.x < 0.5 && uCenterSwitch == 0)) {
            texCoords.x = 0.5 - (texCoords.x - uCenter);
            //texCoords.x = 0.0;
        } else {
            texCoords.x += uCenter;
        }
        if (mod(texCoords.y + uStripeOffset, 0.1) < 0.035) {
            texCoords.x = 0.0;
        }
        */

        if (texCoords.x > 0.5) {
            texCoords.x = 0.5 - (texCoords.x - 0.5);
        } else {
            //texCoords.x += uCenter;
        }

        //texCoords = vec2(0.0);
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
    } else if (uMode == 4) {
        if (texCoords.x < uDoubleCenter) {
            texCoords.x = uDoubleCenter + (-1.0) * (texCoords.x - uDoubleCenter);
        } else if (texCoords.x > 1.0 - uDoubleCenter) {
            float t = 1.0 - uDoubleCenter;
            texCoords.x = t + (-1.0) * (texCoords.x - t);
        }
    } else if (uMode == 5) {
        if (texCoords.y < uDoubleCenter) {
            texCoords.y = uDoubleCenter + (-1.0) * (texCoords.y - uDoubleCenter);
        } else if (texCoords.y > 1.0 - uDoubleCenter) {
            float t = 1.0 - uDoubleCenter;
            texCoords.y = t + (-1.0) * (texCoords.y - t);
        }
    }

    return texture2D(uInputTexture, texCoords);
}

