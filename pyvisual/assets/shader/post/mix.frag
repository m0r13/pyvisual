#version 150
uniform sampler2D uInputTexture;
uniform sampler2D uSource;
uniform float uAlpha;

in vec2 TexCoord0;

out vec4 oFragColor;

void main() {
    vec2 texCoords = TexCoord0;

    oFragColor = mix(texture2D(uInputTexture, texCoords), texture2D(uSource, texCoords), uAlpha);
}

