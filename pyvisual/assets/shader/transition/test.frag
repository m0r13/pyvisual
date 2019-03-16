#version 150

uniform sampler2D uInputTexture; // {"skip" : true, "alias" : "input"}
uniform sampler2D uDestinationTexture; // {"skip" : true, "alias" : "destination"}
uniform float uAlpha; // {"skip" : true, "alias" : "alpha"}

uniform float uCount; // {"default" : 3.0}

in vec2 TexCoord0;
out vec4 oFragColor;

void main() {
    float width = 1.0 / 7.0;
    float rel_x = mod(TexCoord0.x, width);
    float start_x = TexCoord0.x - rel_x;

    rel_x -= width * uAlpha;

    vec4 frag;
    vec2 uv = TexCoord0;
    if (rel_x < 0) {
        uv.x = start_x + rel_x + width;
        frag = texture(uDestinationTexture, uv);
    } else {
        uv.x = start_x + rel_x;
        frag = texture(uInputTexture, uv);
    }

    /*
    vec4 frag1 = texture(uInputTexture, TexCoord0);
    vec4 frag2 = texture(uDestinationTexture, TexCoord0);

    oFragColor = mix(frag1, frag2, uAlpha);
    */
    oFragColor.x = rel_x;
    oFragColor.yz = vec2(0.0);
    oFragColor.w = 1.0;

    oFragColor = frag;
}

