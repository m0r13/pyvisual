#version 150
uniform sampler2D uInputTexture; // {"skip" : true}
uniform vec4 uColor; // {"skip" : true}

in vec2 TexCoord0;

out vec4 oFragColor;

void main() {
    oFragColor = uColor;
}

