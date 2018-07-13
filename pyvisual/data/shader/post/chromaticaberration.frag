#version 150
uniform sampler2D uInputTexture;
uniform vec4 uDirections;
uniform vec4 uDirectionsOffset;

in vec2 TexCoord0;

out vec4 oFragColor;

void main() {
    ivec2 size = textureSize(uInputTexture, 0);
    vec2 sizeDivider = vec2(size.x, size.y);
    vec2 redDirection = vec2(cos(uDirections.r), sin(uDirections.r));
    vec2 greenDirection = vec2(cos(uDirections.g), sin(uDirections.g));
    vec2 blueDirection = vec2(cos(uDirections.b), sin(uDirections.b));
    vec2 alphaDirection = vec2(cos(uDirections.a), sin(uDirections.a));

    vec4 color;
    color.r = texture2D(uInputTexture, TexCoord0 + redDirection * uDirectionsOffset.r / sizeDivider).r;
    color.g = texture2D(uInputTexture, TexCoord0 + greenDirection * uDirectionsOffset.g / sizeDivider).g;
    color.b = texture2D(uInputTexture, TexCoord0 + blueDirection * uDirectionsOffset.b / sizeDivider).b;
    color.a = texture2D(uInputTexture, TexCoord0 + alphaDirection * uDirectionsOffset.a / sizeDivider).a;
    oFragColor = color;
}

