#define DONT_SAMPLE_FRAGMENT
#include <filter/basefilter.frag>

#include <lib/transform.glsl>

// preprocessor int dInputWrapping; {"choices" : ["none", "repeat", "mirrored repeat"], "default" : 2, "group" : "additional"}
// preprocessor int dBlendMode; {"choices" : ["max", "multiply", "difference", "screen", "add factored", "add-1"], "default" : 0, "group" : "additional"}

uniform mat4 uInputTransform;
uniform float uAspectAdjust; // {"default" : 1.0}
uniform float uAxisAngle; // {"alias" : "axis_angle", "unit" : "deg"}
uniform float uAngleOffset; // {"alias" : "angle", "unit" : "deg"}
uniform int uSegmentCount; // {"alias" : "segments", "default" : 4, "range" : [0, Infinity]}
uniform int uSecondarySegmentCount; // {"alias" : "segments1", "default" : 2, "range" : [0, Infinity]}
uniform bool uGuide; // {"default" : 0}

vec2 uvToPolar(vec2 uv) {
    ivec2 size = textureSize(uInputTexture, 0);
    vec2 texCoords = (uv - vec2(0.5)) * 2.0;
    texCoords.x *= mix(1.0, float(size.x) / float(size.y), uAspectAdjust);

    float radius = length(texCoords);
    // this was an accident: interesting WTF
    // float angle = radians(atan(texCoords.y, texCoords.x)) + 3.141595;
    float angle = atan(texCoords.y, texCoords.x) + 3.141595 * 0.5;

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
    if (n < 0.001) {
        return polar;
    }
    float modAngle = radians(360.0) / n;
    polar.x = mod(polar.x + radians(uAxisAngle), modAngle);
    if (polar.x > modAngle / 2) {
        polar.x = modAngle - polar.x;
    }
    return polar;
}

vec4 sampleMirroredFrag(vec2 uv) {
    if (dInputWrapping == 0) {
        if (uv.x < 0.0 || uv.y < 0.0 || uv.x > 1.0 || uv.y > 1.0) {
            return vec4(vec3(0.0), 1.0);
        }
    } else if (dInputWrapping == 1) {
        uv = fract(uv);
    } else if (dInputWrapping == 2) {
        // TODO haha
        // I was too lazy to find out a formula for mirrored repeat
        // it's already mirrored repeated when the input texture is on that by default
    }

    uv = transformUV(uv, uInputTransform, textureSize(uInputTexture, 0));
    return texture2D(uInputTexture, uv);
}

vec4 samplePolarMirrorGuide(vec2 polar, vec4 frag) {
    // some things are similar to polarMirror function above
    float modAngle = radians(360.0) / uSegmentCount;
    vec2 adjustedPolar = polar;
    adjustedPolar.x += radians(uAngleOffset) - 3.141595 * 0.5 + radians(uAxisAngle);
    frag = sampleMirroredFrag(polarToUV(adjustedPolar));
    float aa = mod(polar.x + radians(uAxisAngle), radians(360.0));
    float a = mod(aa, modAngle);

    float width = radians(1.5);
    // red lines show primary axes
    if (a < width || a > modAngle - width) {
        frag = mix(frag, vec4(1.0, 0.0, 0.0, 1.0), 0.5);
    }
    // blue lines show mirroring between primary axes
    if (abs(a - modAngle / 2) < width) {
        frag = mix(frag, vec4(0.0, 0.0, 1.0, 1.0), 0.5);
    }
    // green overlay for the original image area that is repeated
    if (aa >= 0.0 && aa < modAngle / 2) {
        frag = mix(frag, vec4(0.0, 1.0, 0.0, 1.0), 0.25);
    }
    return frag;
}

vec4 filterFrag(vec2 uv, vec4 _) {
    vec2 size = textureSize(uInputTexture, 0);

    vec2 polar = uvToPolar(uv);

    vec2 polar0 = polarMirror(polar, uSegmentCount);
    polar0.x += radians(uAngleOffset) - 3.141595 * 0.5;
    vec2 uv0 = polarToUV(polar0);

    vec4 frag = sampleMirroredFrag(uv0);
    if (uGuide) {
        frag = samplePolarMirrorGuide(polar, frag);
    } else if (uSecondarySegmentCount != 0) {
        vec2 polar1 = polarMirror(polar, uSecondarySegmentCount);
        polar1.x += radians(uAngleOffset) - 3.141595 * 0.5;
        vec2 uv1 = polarToUV(polar1);

        vec4 frag1 = sampleMirroredFrag(uv1);
        if (dBlendMode == 0) {
            // manchmal übersteuert
            frag = max(frag, frag1);
        } else if (dBlendMode == 1) {
            // hält farbe ganz nice
            frag = frag * frag1;
        } else if (dBlendMode == 2) {
            frag = vec4(abs(frag - frag1).rgb, frag.a);
        } else if (dBlendMode == 3) {
            // etwas knallig übersteuerte farben, aber nice
            frag = (1 - (1 - frag) / frag1);
        } else if (dBlendMode == 4) {
            frag = 0.75 * frag + 0.5 * frag1;
        } else if (dBlendMode == 5) {
            // auch etwas knallige farben, aber noch mehr details moduliert
            frag = frag + frag1 - 1.0;
        }
        // overlay:
        /*
        float a = frag.a;
        vec4 base = frag;
        vec4 blend = frag1;
        frag = mix(1.0 - 2.0 * (1.0 - base) * (1.0 - blend), 2.0 * base * blend, step(base, vec4(0.5)));
        frag.a = a;
        */
    }

    return vec4(frag.rgb, frag.a);
}

