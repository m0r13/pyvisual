#define DONT_SAMPLE_FRAGMENT
#include <filter/basefilter.frag>

uniform vec2 uResolution; // {"default" : [100, 100]}
uniform int uAspectCorrect; // {"default" : 1}

vec4 filterFrag(vec2 uv, vec4 frag) {
    vec2 resolution = uResolution;
    if (uAspectCorrect > 0) {
        vec2 size = textureSize(uInputTexture, 0);
        float aspect = size.y / size.x;
        resolution.y = resolution.x * aspect;
    }
    uv = floor(uv * resolution) / resolution;
    return texture2D(uInputTexture, uv);
}

