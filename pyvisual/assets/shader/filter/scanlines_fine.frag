#include <filter/basefilter.frag>

uniform float time;
uniform float count;
uniform float noiseAmount; // {"default" : 0.1}
uniform float linesAmount; // {"default" : 0.1}

#define PI 3.14159265359

highp float rand( const in vec2 uv ) {
    const highp float a = 12.9898, b = 78.233, c = 43758.5453;
    highp float dt = dot( uv.xy, vec2( a,b ) ), sn = mod( dt, PI );
    return fract(sin(sn) * c);
}

vec4 filterFrag(vec2 uv, vec4 frag) {
    float height = textureSize(uInputTexture, 0).y;
    height = 1.0f;
    vec4 cTextureScreen = frag;
    float dx = rand( uv + time );
    vec3 cResult = cTextureScreen.rgb * dx * noiseAmount;
    float lineAmount = height * 1.8 * count;
    vec2 sc = vec2( sin( uv.y * lineAmount), cos( uv.y * lineAmount) );
    cResult += cTextureScreen.rgb + cTextureScreen.rgb * vec3( sc.x, sc.y, sc.x ) * linesAmount;
    return vec4( cResult, cTextureScreen.a );
}

