#include <filter/basefilter.frag>

uniform sampler2D uMask;
uniform float uAngle;

vec4 filterFrag(vec2 uv, vec4 frag) {
    vec2 size = textureSize(uInputTexture, 0);
    vec2 mask = texture2D(uMask, uv).gb;

    float theta = 3.141595 * 0.25;
    theta = atan(mask.y, mask.x) + radians(uAngle) * 0.0;
    // background is excluded by default due to some weird math thing when length(mask) == 0.0
    /*
    if (length(mask) < 0.1) {
        theta = radians(uAngle);
    }
    */
    vec2 texCoords = uv;
    texCoords -= 0.5;
    texCoords.x *= size.x / size.y;

    float s = sin(theta);
    float c = cos(theta);
    mat2 m = mat2(c, -s, s, c);
    texCoords = m * texCoords;

    texCoords.x /= size.x / size.y;
    texCoords += 0.5;

    return texture2D(uInputTexture, texCoords);
}

