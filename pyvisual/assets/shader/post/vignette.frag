#version 150
uniform sampler2D uInputTexture;
uniform float uRadius;
uniform vec2 uRadiusFactor;
uniform float uSoftness;
uniform float uIntensity;
uniform float uDistanceOrder;

in vec2 TexCoord0;

out vec4 oFragColor;

float minkowski(vec2 a, vec2 b, float p) {
    return pow(pow(abs(a.x - b.x), p) + pow(abs(a.y - b.y), p), 1.0 / p);
}

void main() {
    vec2 radiusAdjust = vec2(uRadius, uRadius) * uRadiusFactor;

    // position uv coordinates around (0.5, 0.5)
    vec2 offset = vec2(0.5, 0.5);
    vec2 center = vec2(0.5, 0.5) - offset;
    vec2 uv = TexCoord0 - offset;
    float d = minkowski(center, uv * radiusAdjust, uDistanceOrder) * 2.0;

    // prevent math errors
    float softness = max(0.0001, uSoftness);
    float v = smoothstep(1.0 + softness / 2.0, 1.0 - softness / 2.0, d);
    // apply intensity
    v = (1.0 - v) * uIntensity;
    v = 1.0 - v;

    vec4 frag = texture2D(uInputTexture, TexCoord0);
    oFragColor = vec4(frag.rgb * v, frag.a);
}

