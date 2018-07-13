#version 150

uniform sampler2D uInputTexture;

in vec2 TexCoord0;
out vec4 oFragColor;

void main() {
    vec4 frag = texture(uInputTexture, TexCoord0);
    oFragColor = vec4(frag.r, vec2(0.0), frag.a);
}

