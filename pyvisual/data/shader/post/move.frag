#version 150
uniform sampler2D uInputTexture;
//uniform float uDirection;
//uniform float uDirectionOffset;
uniform mat3 uTransform;

in vec2 TexCoord0;

out vec4 oFragColor;

void main() {
    ivec2 size = textureSize(uInputTexture, 0);
    vec2 sizeDivider = vec2(size.x, size.y);
    //vec2 direction = vec2(cos(uDirection), sin(uDirection));
    //vec2 texCoords = TexCoord0 + direction * uDirectionOffset / sizeDivider;
    vec2 texCoords = (uTransform * vec3(TexCoord0, 1.0)).xy;
    /*
    if (int(floor(texCoords.x)) % 2 == 0) {
        texCoords.x = fract(texCoords.x);
    } else {
        texCoords.x = 1 - fract(texCoords.x);
    }
    if (int(floor(texCoords.y)) % 2 == 0) {
        texCoords.y = fract(texCoords.y);
    } else {
        texCoords.y = 1 - fract(texCoords.y);
    }
    */
    oFragColor = texture2D(uInputTexture, texCoords);
}

