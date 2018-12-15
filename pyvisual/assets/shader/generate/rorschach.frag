#include <generate/base_time_mask.frag>

#include <lib/noise3D.glsl>

uniform float uThreshold; // {"default" : 0.68}
uniform float uSoftness; // {"default" : 0.06}
uniform float uShadeContrast; // {"default" : 0.55}

uniform vec2 uOffset;
uniform float uTest;
uniform 

float fbm(vec3 p) {
    float f = 0.0;
    float frequency = 1.0; // 1.0
    float amplitude = 0.5; // 0.5
    float lsomething = uTest;
    for (int i = 0; i < 4; i++) {
        f += snoise(p * frequency) * amplitude;
        amplitude *= lsomething;
        frequency *= 2.0 + float(i) / 100.0;
    }
    return min(1.0, f);
}

void generateFrag() {
    vec2 uv = 1.0 - pyvisualUV * 1.0;
    uv.x = 1.0 - abs(1.0 - uv.x * 2.0); 

    //oFragColor = vec4(uv.x, 0.0, 0.0, 1.0);

    vec3 p = vec3(uv + uOffset, pyvisualTime * 0.01);

    float blot = fbm(p * 3.0 + 8.0);
    float shade = fbm(p * 2.0 + 16.0);
    float shadeContrast = uShadeContrast;

    blot = blot + (sqrt(uv.x) - abs(0.5 - uv.y));
    blot = smoothstep(uThreshold - uSoftness / 2.0, uThreshold + uSoftness / 2.0, blot) * max(1.0 - shade * shadeContrast, 0.0);

    pyvisualOutColor = vec4(vec3(blot), 1.0);
}

