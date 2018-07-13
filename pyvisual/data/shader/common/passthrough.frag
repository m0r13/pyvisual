#version 150

uniform sampler2D uInputTexture;

in vec2 TexCoord0;
out vec4 oFragColor;

void main() {
    oFragColor = texture(uInputTexture, TexCoord0);
}

