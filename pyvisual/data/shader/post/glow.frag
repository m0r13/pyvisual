#version 150

uniform sampler2D uInputTexture;
uniform float size;
uniform float amount;
uniform float darkness;

in vec2 TexCoord0;

out vec4 oFragColor;

void main() {
    ivec2 resolution = textureSize(uInputTexture, 0);
    float h = size / float(resolution.x);
    float v = size / float(resolution.y);
    vec4 sum = vec4( 0.0 );
    sum += (texture2D(uInputTexture, vec2( TexCoord0.x - 4.0 * h, TexCoord0.y ) )- darkness) * 0.051 ;
    sum += (texture2D(uInputTexture, vec2( TexCoord0.x - 3.0 * h, TexCoord0.y ) )- darkness) * 0.0918;
    sum += (texture2D(uInputTexture, vec2( TexCoord0.x - 2.0 * h, TexCoord0.y ) )- darkness) * 0.12245;
    sum += (texture2D(uInputTexture, vec2( TexCoord0.x - 1.0 * h, TexCoord0.y ) )- darkness) * 0.1531;
    sum += (texture2D(uInputTexture, vec2( TexCoord0.x, TexCoord0.y ) )- darkness) * 0.1633;
    sum += (texture2D(uInputTexture, vec2( TexCoord0.x + 1.0 * h, TexCoord0.y ) )- darkness) * 0.1531;
    sum += (texture2D(uInputTexture, vec2( TexCoord0.x + 2.0 * h, TexCoord0.y ) )- darkness) * 0.12245;
    sum += (texture2D(uInputTexture, vec2( TexCoord0.x + 3.0 * h, TexCoord0.y ) )- darkness) * 0.0918;
    sum += (texture2D(uInputTexture, vec2( TexCoord0.x + 4.0 * h, TexCoord0.y ) )- darkness) * 0.051;
    sum += (texture2D(uInputTexture, vec2( TexCoord0.x, TexCoord0.y - 4.0 * v ) )- darkness) * 0.051;
    sum += (texture2D(uInputTexture, vec2( TexCoord0.x, TexCoord0.y - 3.0 * v ) )- darkness) * 0.0918;
    sum += (texture2D(uInputTexture, vec2( TexCoord0.x, TexCoord0.y - 2.0 * v ) )- darkness) * 0.12245;
    sum += (texture2D(uInputTexture, vec2( TexCoord0.x, TexCoord0.y - 1.0 * v ) )- darkness) * 0.1531;
    sum += (texture2D(uInputTexture, vec2( TexCoord0.x, TexCoord0.y ) )- darkness) * 0.1633;
    sum += (texture2D(uInputTexture, vec2( TexCoord0.x, TexCoord0.y + 1.0 * v ) )- darkness) * 0.1531;
    sum += (texture2D(uInputTexture, vec2( TexCoord0.x, TexCoord0.y + 2.0 * v ) )- darkness) * 0.12245;
    sum += (texture2D(uInputTexture, vec2( TexCoord0.x, TexCoord0.y + 3.0 * v ) )- darkness) * 0.0918;
    sum += (texture2D(uInputTexture, vec2( TexCoord0.x, TexCoord0.y + 4.0 * v ) )- darkness) * 0.051;
    vec4 base = texture2D(uInputTexture, TexCoord0 );
    gl_FragColor = base + max(sum,0.0) * amount;
}
