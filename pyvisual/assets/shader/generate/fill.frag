#version 150
uniform sampler2D uInputTexture;
uniform vec4 uColor;

in vec2 TexCoord0;

out vec4 oFragColor;

void main() {
    oFragColor = uColor;
}

