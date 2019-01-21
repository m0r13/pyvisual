#include <generate/timemasked/base.frag>

uniform mat4 uTransform;
uniform float uAspectAdjust; // {"default" : 1.0}
uniform float uThreshold; // {"default" : 0.5}
uniform float uBorderWidth; // {"default" : 0.0}
uniform float uInnerSoftness; // {"default" : 0.1, "range" : [0.0001, Infinity]}
uniform float uOuterSoftness; // {"default" : 0.1, "range" : [0.0001, Infinity]}

#define ENABLE_TIME

#ifdef ENABLE_TIME
#include <lib/noise3D.glsl>
#else
#include <lib/noise2D.glsl>
#endif

void generateFrag() {
    vec2 size = textureSize(uInputTexture, 0);
    vec2 uv = pyvisualUV.xy - vec2(0.5);
    // TODO do in px coordinates?
    uv = (uTransform * vec4(uv, 0.0, 1.0)).xy;
    uv.x *= mix(1.0, float(size.x) / float(size.y), uAspectAdjust);

#ifdef ENABLE_TIME
    vec3 p = vec3(uv, pyvisualTime);
#else
    vec2 p = uv;
#endif
    float noise = snoise(p);

    //float v = smoothstep(0.47, 0.53, noise);
    float v = noise;

    float threshold = uThreshold;
    //v *= 1.0 - smoothstep(softness1 / 2.0, softness1, max(0.0, threshold - noise));
    //v *= 1.0 - smoothstep(0.0, softness2, max(0.0, noise - threshold));

    // simple threshold
    v = step(threshold, v);
    // "outer" border
    v = 1.0 - smoothstep(uBorderWidth / 2.0, uBorderWidth / 2.0 + uInnerSoftness, max(0.0, threshold - noise));
    // "inner" border"
    v *= 1.0 - smoothstep(uBorderWidth / 2.0, uBorderWidth / 2.0 + uOuterSoftness, max(0.0, noise - threshold));

    pyvisualOutColor = vec4(vec3(v), 1.0);
}
