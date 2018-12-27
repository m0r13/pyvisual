#version 150

uniform sampler2D uInputTexture;
uniform float uValue;
uniform float uAlpha;

in vec2 TexCoord0;

out vec4 oFragColor;

void main() {
    vec4 frag = texture(uInputTexture, TexCoord0);
    oFragColor = vec4(frag.rgb * uValue, frag.a * uAlpha);
}

