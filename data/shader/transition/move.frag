uniform sampler2D uInputTexture,uTexture1, uTexture2;
uniform float uAlpha;
//uniform vec2 resolution;

in vec2 TexCoord0;
out vec4 oFragColor;

void main() {
    vec4 frag;
    if (TexCoord0.x < (1.0f - uAlpha)) {
        frag = texture(uTexture1, TexCoord0 + vec2(uAlpha, 0.0f));
    } else {
        frag = texture(uTexture2, TexCoord0 + vec2(-1.0f + uAlpha, 0.0f));
    }

    oFragColor = frag;
}
