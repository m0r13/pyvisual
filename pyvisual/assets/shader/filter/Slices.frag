#define DONT_SAMPLE_FRAGMENT
#include <filter/basefilter.frag>

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
    float n = noise1d(uv.y * slices + /*timeH **/ timeV * 3.0);
    float ns = steppedVal(fract(n  ),slices) + 2.0;
    float nsr = random1d(ns);
    vec2 uvn = uv;
    uvn.x += nsr * sin(timeH * TWO_PI + nsr * 20.0) * offset / textureSize(uInputTexture, 0).x;
    return texture2D(uInputTexture, uvn);
}
