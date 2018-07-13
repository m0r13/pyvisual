#version 150

uniform mat4 uModelViewProjection;

in vec2 iPosition;
in vec2 iTexCoord;

out vec2 TexCoord0;

void main(void) {
    gl_Position = uModelViewProjection * vec4(iPosition, 0.0, 1.0);
    TexCoord0 = iTexCoord;
}

