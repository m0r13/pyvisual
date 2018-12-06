#version 150

uniform mat4 uModelViewProjection; // {"skip" : true}
uniform vec2 uTextureSize; // {"skip" : true}
uniform mat4 uTransformUV; // {"skip" : true, "alias" : "transformUV"}

in vec2 iPosition;
in vec2 iTexCoord;

out vec2 TexCoord0;

void main(void) {
    gl_Position = uModelViewProjection * vec4(iPosition, 0.0, 1.0);

    vec2 pixelTexCoords = iTexCoord * uTextureSize - uTextureSize * 0.5f;
    pixelTexCoords = (uTransformUV * vec4(pixelTexCoords, 0.0, 1.0)).xy;
    vec2 texCoords = (pixelTexCoords + uTextureSize * 0.5f) / uTextureSize;
    
    TexCoord0 = texCoords;
}

