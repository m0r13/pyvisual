#include <generate/timemasked/base.frag>

uniform float uCountX;
uniform float uCountY;

void generateFrag() {
    pyvisualUV -= vec2(0.5, 0.0);

    float modX = 2.0 / (uCountX * 2.0 + 0.0001);
    float modY = 2.0 / (uCountY * 2.0 + 0.0001);

    bool x = mod(pyvisualUV.x, modX) < 0.5 * modX;
    bool y = mod(pyvisualUV.y, modY) < 0.5 * modY;

    float value = (x && !y) || (!x && y) ? 1.0 : 0.0;

    pyvisualOutColor = vec4(vec3(value), 1.0);
}

