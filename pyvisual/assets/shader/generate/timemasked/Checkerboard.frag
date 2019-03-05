#include <generate/timemasked/base.frag>

uniform float uCountX;
uniform float uCountY;
uniform int uCenter; // {"default" : 1}

// TODO implement softness!
uniform float uSoftness0; // {"default" : 0.005}
uniform float uSoftness1; // {"default" : 0.005}

void generateFrag() {
    if (uCenter > 0) {
        pyvisualUV -= vec2(0.5, 0.5);
    }

    float modX = 2.0 / (uCountX * 2.0 + 0.0001);
    float modY = 2.0 / (uCountY * 2.0 + 0.0001);

    bool y = mod(pyvisualUV.y, modY) < 0.5 * modY;
    bool x = mod(pyvisualUV.x, modX) < 0.5 * modX;

    float value = (x && !y) || (!x && y) ? 1.0 : 0.0;

    pyvisualOutColor = vec4(vec3(value), 1.0);
}

