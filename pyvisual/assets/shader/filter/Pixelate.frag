#define DONT_SAMPLE_FRAGMENT
#include <filter/basefilter.frag>

#include <lib/transform.glsl>

uniform mat4 uPreTransform;
uniform vec2 uResolution; // {"default" : [100, 100]}
uniform bool uAspectCorrect; // {"default" : 1}

vec4 filterFrag(vec2 uv, vec4 frag) {
    vec2 resolution = uResolution;
    if (uAspectCorrect) {
        vec2 size = textureSize(uInputTexture, 0);
        float aspect = size.y / size.x;
        resolution.y = resolution.x * aspect;
    }

    uv = floor(uv * resolution) / resolution;
    uv = transformUV(uv, uPreTransform, textureSize(uInputTexture, 0));
    return texture2D(uInputTexture, uv);
}

