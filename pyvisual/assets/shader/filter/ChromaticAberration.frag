#include <filter/basefilter.frag>

uniform vec2 uRedOffset;
uniform vec2 uGreenOffset;
uniform vec2 uBlueOffset;

vec4 filterFrag(vec2 uv, vec4 frag) {
    ivec2 size = textureSize(uInputTexture, 0);
    vec2 sizeDivider = vec2(size.x, size.y);

    vec4 color;
    color.r = texture2D(uInputTexture, uv + uRedOffset / sizeDivider).r;
    color.g = texture2D(uInputTexture, uv + uGreenOffset / sizeDivider).g;
    color.b = texture2D(uInputTexture, uv + uBlueOffset / sizeDivider).b;
    color.a = frag.a;
    return color;
}

