
#define DONT_SAMPLE_FRAGMENT
#include <filter/basefilter.frag>

uniform sampler2D uOtherTexture;

uniform int uCount; // {"default" : 1, "range" : [0, Infinity]}
uniform float uStepSize;
uniform bool uOriginalInside; // {"default" : false}

vec4 filterFrag(vec2 uv, vec4 frag) {
    vec2 origUV = uv;
    uv = (uv - 0.5) * 2.0;

    vec2 size = textureSize(uInputTexture, 0);
    vec2 referenceUV = uv;
    //referenceUV.x /= size.x / size.y;

    float s = uStepSize * 0.1;
    float t = 1.0 + s;
    int j;
    for (int i = 0; i < uCount; i++) {
        t = t - s;
        if (abs(referenceUV.x) < t && abs(referenceUV.y) < t) {
            uv /= t;
            //uv /= (1.0 - uStepSize);
            j = i;
        }
    }

    /*
    float a = j / float(uCount - 1);
    return vec4(a, 0.0, 0.0, 1.0);
    */

    uv = (uv * 0.5) + 0.5;

    j = uCount - 1 - j;
    if (j == 0 && uOriginalInside) {
        uv = origUV;
    }
    return mod(j, 2) == 0 ? texture2D(uInputTexture, uv) : texture2D(uOtherTexture, uv);
}
