#version 150
uniform sampler2D uInputTexture;
uniform vec2 uOffset;
uniform vec4 uColor;

in vec2 TexCoord0;
out vec4 oFragColor;

void main() {
    ivec2 size = textureSize(uInputTexture, 0);
    vec2 shadowOffset = uOffset / vec2(size);

    vec4 color = texture(uInputTexture, TexCoord0);
    vec4 colorTranslated = texture(uInputTexture, TexCoord0 - shadowOffset);
    vec4 mask = vec4(uColor.rgb, uColor.a * colorTranslated.a);
    oFragColor = vec4(color.rgb * color.a + mask.rgb * (1.0 - color.a), color.a + mask.a * (1.0 - color.a));
}

