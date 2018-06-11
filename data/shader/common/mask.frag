#version 150
uniform sampler2D uInputTexture;
uniform sampler2D uMaskTexture;

in vec2 TexCoord0;

out vec4 oFragColor;

void main() {
    vec4 color = texture(uInputTexture, TexCoord0);
    vec4 mask = texture(uMaskTexture, TexCoord0);

    oFragColor = vec4(color.rgb, mask.r);
}

