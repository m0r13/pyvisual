uniform sampler2D uInputTexture;
uniform mat4 uTransform;
uniform float uTime;
uniform float uValueFactor;
uniform float uValueOffset;
uniform float uValueThreshold;
uniform float uValueSoftness;

in vec2 TexCoord0;

out vec4 oFragColor;

#include <lib/noise3D.glsl>

void main() {
    vec2 size = textureSize(uInputTexture, 0);
    vec2 uv = TexCoord0.xy - vec2(0.5);
    uv.x *= float(size.x) / float(size.y);
    uv = (uTransform * vec4(uv, 0.0, 1.0)).xy;

    vec3 position = vec3(uv, uTime * 1.0);
    float v = snoise(position) / 2.0 + 0.5;
    v = (v * uValueFactor) + uValueOffset;
    float softness = uValueSoftness;
    //float softness2 = uValueSoftness / 2.0;
    // commented code was to show only edges around uValueThreshold
    //if (v > uValueThreshold + 0.1) {
    //    v *= 1.0 - smoothstep(uValueThreshold + 0.1, uValueThreshold + 0.1 + softness2, v);
    //} else {
        v = smoothstep(uValueThreshold - softness / 2.0, uValueThreshold + softness / 2.0, v);
    //}
    oFragColor = vec4(vec3(v), 1.0);
}
