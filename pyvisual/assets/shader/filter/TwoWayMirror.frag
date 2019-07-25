#define DONT_SAMPLE_FRAGMENT
#include <filter/basefilter.frag>

#include <lib/transform.glsl>

uniform mat4 uPreTransform;

vec4 filterFrag(vec2 uv, vec4 _) {
    /*
    // uMode == 0 is just passthrough
    if (uMode == 1) {
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
    */

    vec2 mirroredUV = uv;
    //if (mirroredUV.y > 0.5) {
        mirroredUV.y = 0.5 - (mirroredUV.y - 0.5);
    //}

    vec4 frag0 = texture2D(uInputTexture, uv);
    vec4 frag1 = texture2D(uInputTexture, mirroredUV);

    vec4 frag = vec4(vec3(0.0), 1.0);
    frag.rgb = frag0.rgb + frag1.rgb;

    return frag;
}

