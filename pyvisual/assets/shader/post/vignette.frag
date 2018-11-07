#version 150
uniform sampler2D uInputTexture;
uniform float uRadius;
uniform vec2 uRadiusFactor;
uniform float uSoftness;
uniform float uIntensity;

in vec2 TexCoord0;

out vec4 oFragColor;

void main() {
    vec2 radiusAdjust = vec2(uRadius, uRadius) * uRadiusFactor;
    float d = length((vec2(0.5, 0.5) - TexCoord0) * radiusAdjust) * 2.0;

    // prevent math errors
    float softness = max(0.0001, uSoftness);
    float v = smoothstep(1.0 + softness / 2.0, 1.0 - softness / 2.0, d);
    // apply intensity
    v = (1.0 - v) * uIntensity;
    v = 1.0 - v;

    vec4 frag = texture2D(uInputTexture, TexCoord0);
    oFragColor = vec4(frag.rgb * v, frag.a);
}

