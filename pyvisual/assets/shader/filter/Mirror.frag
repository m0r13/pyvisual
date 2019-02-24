#define DONT_SAMPLE_FRAGMENT
#include <filter/basefilter.frag>

uniform int uMode; // {"default" : 1, "choices" : ["passthrough", "1", "2", "3"]}
uniform float uCenter; // {"default" : 0.5}
uniform int uCenterSwitch; // {"default" : 0}
uniform float uStripeOffset; // {"default" : 0.0}

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
    }

    return texture2D(uInputTexture, texCoords);
}

