#define DONT_SAMPLE_FRAGMENT
#include <filter/basefilter.frag>

uniform float uAxisAngle; // {"alias" : "axis_angle"}
uniform float uAngleOffset; // {"alias" : "angle"}
uniform float uSegmentCount; // {"alias" : "segments", "default" : 5, "range" : [0, Infinity]}

vec4 filterFrag(vec2 uv, vec4 _) {
    vec2 texCoords = (uv - vec2(0.5)) * 2.0;
    texCoords.x *= 1920.0 / 1080.0;

    float radius = length(texCoords);
    // this was an accident: interesting WTF
    // float angle = radians(atan(texCoords.y, texCoords.x)) + 3.141595;
    float angle = atan(texCoords.y, texCoords.x) + 3.141595;

    float modAngle = radians(360.0) / uSegmentCount;
    angle = mod(angle + radians(uAxisAngle), modAngle);
    if (angle > modAngle / 2) {
        angle = modAngle - angle;
    }

    //oFragColor = vec4(radius, radius, radius, 1.0);
    //oFragColor = vec4(vec3(angle / radians(360.0)), 1.0);

    angle -= 3.141595;
    angle += radians(uAngleOffset);
    texCoords.x = radius * cos(angle);
    texCoords.y = radius * sin(angle);
    //texCoords.x /= 1920.0 / 1080.0;
    texCoords = (texCoords + vec2(1.0)) / 2.0;

    vec4 frag2 = texture2D(uInputTexture, texCoords);
    return vec4(frag2.r, frag2.g, frag2.b, 1.0);
}

