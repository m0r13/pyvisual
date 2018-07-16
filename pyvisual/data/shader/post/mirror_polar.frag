#version 150
uniform sampler2D uInputTexture;
uniform float uAngleOffset;
uniform float uSegmentCount;

in vec2 TexCoord0;

out vec4 oFragColor;

void main() {
    vec2 texCoords = (TexCoord0 - vec2(0.5)) * 2.0;
    texCoords.x *= 1920.0 / 1080.0;

    float radius = length(texCoords);
    float angle = atan(texCoords.y, texCoords.x) + 3.141595;

    float modAngle = radians(360) / 4;
    angle = mod(angle, modAngle);
    if (angle > modAngle / 2) {
        angle = modAngle - angle;
    }

    //oFragColor = vec4(radius, radius, radius, 1.0);
    //oFragColor = vec4(vec3(angle / radians(360.0)), 1.0);

    angle -= 3.141595;
    angle += uAngleOffset;
    texCoords.x = radius * cos(angle);
    texCoords.y = radius * sin(angle);
    texCoords.x /= 1920.0 / 1080.0;
    texCoords = (texCoords + vec2(1.0)) / 2.0;

    //oFragColor = vec4(vec3(texCoords.x), 1.0);
    vec4 frag1 = texture2D(uInputTexture, TexCoord0);
    vec4 frag2 = texture2D(uInputTexture, texCoords);
    oFragColor = vec4(frag2.r, frag2.r, frag2.r, 1.0);
}

