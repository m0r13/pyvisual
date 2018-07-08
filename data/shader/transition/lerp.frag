#version 150

uniform sampler2D uInputTexture;
uniform sampler2D uTexture1;
uniform sampler2D uTexture2;
uniform float uAlpha;

in vec2 TexCoord0;
out vec4 oFragColor;

void main() {
    vec4 frag1 = texture(uTexture1, TexCoord0);
    vec4 frag2 = texture(uTexture2, TexCoord0);
    float alpha0 = 1.0f - abs(uAlpha - 1.0f);
    oFragColor = mix(frag1, frag2, alpha0);
}

