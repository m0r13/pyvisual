#version 150

uniform sampler2D uInputTexture;
uniform float time;
uniform float count;
uniform float noiseAmount;
uniform float linesAmount;
//uniform float height;
#define PI 3.14159265359

in vec2 TexCoord0;

out vec4 oFragColor;

highp float rand( const in vec2 uv ) {
    const highp float a = 12.9898, b = 78.233, c = 43758.5453;
    highp float dt = dot( uv.xy, vec2( a,b ) ), sn = mod( dt, PI );
    return fract(sin(sn) * c);
}
void main() {
    float height = textureSize(uInputTexture, 0).y;
    height = 1.0f;
    vec4 cTextureScreen = texture2D( uInputTexture, TexCoord0 );
    float dx = rand( TexCoord0 + time );
    vec3 cResult = cTextureScreen.rgb * dx * noiseAmount;
    float lineAmount = height * 1.8 * count;
    vec2 sc = vec2( sin( TexCoord0.y * lineAmount), cos( TexCoord0.y * lineAmount) );
    cResult += cTextureScreen.rgb * vec3( sc.x, sc.y, sc.x ) * linesAmount;
    cResult = cTextureScreen.rgb + ( cResult );
    oFragColor =  vec4( cResult, cTextureScreen.a );
}
