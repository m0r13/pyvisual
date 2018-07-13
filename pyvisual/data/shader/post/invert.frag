uniform sampler2D uInputTexture;

in vec2 TexCoord0;

out vec4 oFragColor;

void main() {
    vec4 frag = texture2D(uInputTexture, TexCoord0);
    oFragColor = vec4(vec3(1.0) - frag.rgb, frag.a);
}
