#version 150

#include <lib/transform.glsl>

uniform mat4 uModelViewProjection; // {"skip" : true}
uniform vec2 uTextureSize; // {"skip" : true}
uniform mat4 uTransformUV; // {"skip" : true, "alias" : "transformUV"}

in vec2 iPosition;
in vec2 iTexCoord;

out vec2 TexCoordi;
out vec2 TexCoord0;

void main(void) {
    gl_Position = uModelViewProjection * vec4(iPosition, 0.0, 1.0);

    TexCoordi = iTexCoord;
    TexCoord0 = transformUV(iTexCoord, uTransformUV, uTextureSize);
}

