#version 150
uniform sampler2D uInputTexture;

in vec2 TexCoord0;

out vec4 oFragColor;

void main() {
    vec4 mask = texture(uInputTexture, TexCoord0);
    vec4 frag = vec4(0.0);
    if (mask.r > 0.0) {
        frag.rgb = vec3(1.0);
        frag.a = 0.5;
    }

    //oFragColor = vec4(color.rgb, mask.r);
    oFragColor = frag;
}

