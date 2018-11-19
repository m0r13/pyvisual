#version 150
uniform sampler2D uInputTexture;
uniform float uAxisAngle;
uniform float uAngleOffset;
uniform float uSegmentCount;

in vec2 TexCoord0;

out vec4 oFragColor;

void main() {
    vec2 texCoords = (TexCoord0 - vec2(0.5)) * 2.0;
    //texCoords.x *= 1920.0 / 1080.0;

    float radius = length(texCoords);
    // this was an accident: interesting WTF
    // float angle = radians(atan(texCoords.y, texCoords.x)) + 3.141595;
    float angle = atan(texCoords.y, texCoords.x) + 3.141595;

    float modAngle = radians(360.0) / uSegmentCount;
    angle = mod(angle + radians(uAxisAngle), modAngle);
    if (angle > modAngle / 2) {
        angle = modAngle - angle;
    }

    //oFragColor = vec4(radius, radius, radius, 1.0);
    //oFragColor = vec4(vec3(angle / radians(360.0)), 1.0);

    angle -= 3.141595;
    angle += radians(uAngleOffset);
    texCoords.x = radius * cos(angle);
    texCoords.y = radius * sin(angle);
    //texCoords.x /= 1920.0 / 1080.0;
    texCoords = (texCoords + vec2(1.0)) / 2.0;

    //oFragColor = vec4(vec3(texCoords.x), 1.0);
    vec4 frag1 = texture2D(uInputTexture, TexCoord0);
    vec4 frag2 = texture2D(uInputTexture, texCoords);
    oFragColor = vec4(frag2.r, frag2.g, frag2.b, 1.0);
}

