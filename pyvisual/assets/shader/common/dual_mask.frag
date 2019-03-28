#version 150
// uInputTexture is background
uniform sampler2D uInputTexture; // {"skip" : true, "alias" : "input"}
// uInputTexture1 is foreground
uniform sampler2D uInputTexture1; // {"alias" : "foreground"}
uniform sampler2D uMaskTexture; // {"alias" : "mask"}

uniform float uMaskFactor; // {"alias" : "factor", "default" : 1.0}

in vec2 TexCoord0;

out vec4 oFragColor;

void main() {
    // mask mixes between foreground and background
    // mask value 1.0 - foreground
    //            0.0 - background
    vec4 color0 = texture(uInputTexture, TexCoord0);
    vec4 color1 = texture(uInputTexture1, TexCoord0);
    vec4 mask = texture(uMaskTexture, TexCoord0);

    oFragColor = mix(color0, color1, mask.rgbr * uMaskFactor);
}

