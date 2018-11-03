uniform sampler2D uInputTexture;
uniform sampler2D uDestinationTexture;
uniform float uAlpha;
uniform vec2 uDirection;

in vec2 TexCoord0;
out vec4 oFragColor;

void main() {
    vec2 offset = uDirection * uAlpha;
    vec4 frag;
    if (TexCoord0.x < offset.x || TexCoord0.y < offset.y) {
        frag = texture(uDestinationTexture, TexCoord0);
    } else {
        frag = texture(uInputTexture, TexCoord0);
    }

    oFragColor = frag;
}

