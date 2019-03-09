#include <generate/timemasked/base.frag>

uniform float uCountX;
uniform float uCountY;
uniform int uCenter; // {"default" : 1}

// TODO implement softness!
uniform float uSoftness0; // {"default" : 0.005}
uniform float uSoftness1; // {"default" : 0.005}
uniform float uSoftness2; // {"default" : 0.005}
uniform float uSoftness3; // {"default" : 0.005}

float dualSmoothstep(float edge0, float edge1, float value, float smoothness0, float smoothness1) {
    float softValue = 1.0 - smoothstep(edge1-smoothness1*0.5, edge1+smoothness1*0.5, value);
    softValue *= smoothstep(0.0, smoothness0, value);
    return softValue;
}

void generateFrag() {
    if (uCenter > 0) {
        pyvisualUV -= vec2(0.5, 0.5);
    }

    float modX = 2.0 / (uCountX * 2.0 + 0.0001);
    float modY = 2.0 / (uCountY * 2.0 + 0.0001);

    float x = dualSmoothstep(0.0, 0.5*modX, mod(pyvisualUV.x, modX), uSoftness0, uSoftness1);
    float y = dualSmoothstep(0.0, 0.5*modY, mod(pyvisualUV.y, modY), uSoftness2, uSoftness3);

    // non-fuzzy equivalent to next line: (x && !y) || (!x && y)
    float v = abs(x - y);

    pyvisualOutColor = vec4(vec3(v), 1.0);
}

