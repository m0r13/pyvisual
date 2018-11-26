#version 150
uniform sampler2D uInputTexture;
uniform sampler2D uMask;
uniform float uScale0;
uniform float uScale1;

in vec2 TexCoord0;

out vec4 oFragColor;

void main() {
    float mask = texture2D(uMask, TexCoord0).r;

    vec2 texCoords = TexCoord0 - vec2(0.5);
    texCoords *= mix(uScale0, uScale1, mask);
    texCoords += vec2(0.5);

    oFragColor = texture2D(uInputTexture, texCoords);
}

