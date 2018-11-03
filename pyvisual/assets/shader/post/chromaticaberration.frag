#version 150
uniform sampler2D uInputTexture;
uniform vec2 uRedOffset;
uniform vec2 uGreenOffset;
uniform vec2 uBlueOffset;

in vec2 TexCoord0;

out vec4 oFragColor;

void main() {
    ivec2 size = textureSize(uInputTexture, 0);
    vec2 sizeDivider = vec2(size.x, size.y);

    vec4 color;
    color.r = texture2D(uInputTexture, TexCoord0 + uRedOffset / sizeDivider).r;
    color.g = texture2D(uInputTexture, TexCoord0 + uGreenOffset / sizeDivider).g;
    color.b = texture2D(uInputTexture, TexCoord0 + uBlueOffset / sizeDivider).b;
    color.a = texture2D(uInputTexture, TexCoord0).a;
    oFragColor = color;
}

