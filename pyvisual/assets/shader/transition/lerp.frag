#version 150

uniform sampler2D uInputTexture;
uniform sampler2D uDestinationTexture;
uniform float uAlpha;

in vec2 TexCoord0;
out vec4 oFragColor;

void main() {
    vec4 frag1 = texture(uInputTexture, TexCoord0);
    vec4 frag2 = texture(uDestinationTexture, TexCoord0);
    oFragColor = mix(frag1, frag2, uAlpha);
}

