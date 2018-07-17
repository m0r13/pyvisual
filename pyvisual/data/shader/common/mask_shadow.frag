#version 150
uniform sampler2D uInputTexture;
uniform vec2 uOffset;
uniform vec4 uColor;

in vec2 TexCoord0;
out vec4 oFragColor;

void main() {
    ivec2 size = textureSize(uInputTexture, 0);
    vec2 texOffset = uOffset / vec2(size);
    vec4 mask = texture(uInputTexture, TexCoord0 - texOffset);
    vec4 frag = vec4(0.0);
    if (mask.r > 0.0) {
        frag = uColor;
    }

    oFragColor = frag;
}

