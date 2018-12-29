#define DONT_SAMPLE_FRAGMENT
#include <filter/basefilter.frag>

uniform float uAxisAngle; // {"alias" : "axis_angle"}
uniform float uAngleOffset; // {"alias" : "angle"}
uniform int uSegmentCount; // {"alias" : "segments", "default" : 5, "range" : [0, Infinity]}
uniform int uSecondarySegmentCount; // {"alias" : "segments1", "default" : 0, "range" : [0, Infinity]}

vec2 uvToPolar(vec2 uv) {
    ivec2 size = textureSize(uInputTexture, 0);
    vec2 texCoords = (uv - vec2(0.5)) * 2.0;
    texCoords.x *= float(size.x) / float(size.y);

    float radius = length(texCoords);
    // this was an accident: interesting WTF
    // float angle = radians(atan(texCoords.y, texCoords.x)) + 3.141595;
    float angle = atan(texCoords.y, texCoords.x) + 3.141595;

    return vec2(angle, radius);
}

vec2 polarToUV(vec2 polar) {
    vec2 uv;
    uv.x = polar.y * cos(polar.x);
    uv.y = polar.y * sin(polar.x);
    uv = (uv + vec2(1.0)) / 2.0;
    return uv;
}

vec2 polarMirror(vec2 polar, float n) {
    float modAngle = radians(360.0) / n;
    polar.x = mod(polar.x + radians(uAxisAngle), modAngle);
    if (polar.x > modAngle / 2) {
        polar.x = modAngle - polar.x;
    }
    return polar;
}

vec4 filterFrag(vec2 uv, vec4 _) {
    vec2 polar = uvToPolar(uv);

    vec2 polar0 = polarMirror(polar, uSegmentCount);
    polar0.x += radians(uAngleOffset) - 3.141595;
    vec2 uv0 = polarToUV(polar0);

    vec4 frag = texture2D(uInputTexture, uv0);
    if (uSecondarySegmentCount != 0) {
        vec2 polar1 = polarMirror(polar, uSecondarySegmentCount);
        polar1.x += radians(uAngleOffset) - 3.141595;
        vec2 uv1 = polarToUV(polar1);

        vec4 frag1 = texture2D(uInputTexture, uv1);
        frag = max(frag, frag1);
    }

    return vec4(frag.rgb, frag.a);
}

