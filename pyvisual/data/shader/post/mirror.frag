#version 150
uniform sampler2D uInputTexture;
uniform int uMode;

in vec2 TexCoord0;

out vec4 oFragColor;

void main() {
    vec2 texCoords = TexCoord0;
    
    // uMode == 0 is just passthrough
    if (uMode == 1) {
        //texCoords.x = abs(texCoords.x - 0.5);
        if (texCoords.x > 0.5) {
            texCoords.x = 0.5 - (texCoords.x - 0.5);
        }
    } else if (uMode == 2) {
        //texCoords.y = abs(texCoords.y - 0.5);
        if (texCoords.y > 0.5) {
            texCoords.y = 0.5 - (texCoords.y - 0.5);
        }
    } else if (uMode == 3) {
        //texCoords.x = abs(texCoords.x - 0.5);
        //texCoords.y = abs(texCoords.y - 0.5);
        if (texCoords.x > 0.5) {
            texCoords.x = 0.5 - (texCoords.x - 0.5);
        }
        if (texCoords.y > 0.5) {
            texCoords.y = 0.5 - (texCoords.y - 0.5);
        }
    }

    oFragColor = texture2D(uInputTexture, texCoords);
}

