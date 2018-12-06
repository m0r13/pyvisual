#include <filter/basefilter.frag>

uniform float uRadius; // {"default" : 1.0}
uniform vec2 uRadiusFactor; // {"default" : [1.0, 1.0]}
uniform float uDistanceOrder; // {"default" : 2.0, "range" : [0.0, Infinity]}
uniform float uSoftness; // {"default" : 0.35, "range" : [0.0, Infinity]}
uniform float uIntensity; // {"default" : 0.5, "range" : [0.0, 1.0]}

float minkowski(vec2 a, vec2 b, float p) {
    return pow(pow(abs(a.x - b.x), p) + pow(abs(a.y - b.y), p), 1.0 / p);
}

vec4 filterFrag(vec2 uv, vec4 frag) {
    vec2 radiusAdjust = vec2(uRadius, uRadius) * uRadiusFactor;

    // position uv coordinates around (0.5, 0.5)
    vec2 offset = vec2(0.5, 0.5);
    vec2 center = vec2(0.5, 0.5) - offset;
    uv = uv - offset;
    float d = minkowski(center, uv * radiusAdjust, uDistanceOrder) * 2.0;

    // prevent math errors
    float softness = max(0.0001, uSoftness);
    float v = smoothstep(1.0 + softness / 2.0, 1.0 - softness / 2.0, d);
    // apply intensity
    v = (1.0 - v) * uIntensity;
    v = 1.0 - v;

    return vec4(frag.rgb * v, frag.a);
}

