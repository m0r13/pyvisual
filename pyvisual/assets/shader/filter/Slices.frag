#define DONT_SAMPLE_FRAGMENT
#include <filter/basefilter.frag>

#include <lib/transform.glsl>

// preprocessor bool dSymmetric; {"default" : false, "group" : "additional"}

uniform mat4 uTransformGlitch;

uniform float slices; // {"default" : 3.0}
uniform float offset; // {"default" : 100.0}
uniform float timeH; // {"default" : 0.0}
uniform float timeV; // {"default" : 0.0}

float steppedVal(float v, float steps){
    return floor(v*steps)/steps;
}

float random1d(float n){
    return fract(sin(n) * 43758.5453);
}

float noise1d(float p){
    float fl = floor(p);
    float fc = fract(p);
    return mix(random1d(fl), random1d(fl + 1.0), fc);
}

const float TWO_PI = 6.283185307179586;
vec4 filterFrag(vec2 uv, vec4 _) {
    vec2 uu = uv;
    float f = 1.0;
#if dSymmetric
    if (uu.x < 0.5) {
        uu.x = 0.5 - (uu.x - 0.5);
        f = -1.0;
    }
#endif
    vec2 referenceUV = transformUV(uu, uTransformGlitch, textureSize(uInputTexture, 0));
    float n = noise1d(referenceUV.y * slices + /*timeH **/ timeV * 3.0);
    float ns = steppedVal(fract(n  ),slices) + 2.0;
    float nsr = random1d(ns);
    vec2 uvn = uv;
    uvn.x += f * nsr * sin(timeH * TWO_PI + nsr * 20.0) * offset / textureSize(uInputTexture, 0).x;
    return texture2D(uInputTexture, uvn);
}
