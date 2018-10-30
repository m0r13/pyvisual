uniform sampler2D uInputTexture;
uniform float slices;
uniform float offset;
uniform float timeH;
uniform float timeV;

in vec2 TexCoord0;

out vec4 oFragColor;

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
void main() {
    vec2 uv = TexCoord0;
    float n = noise1d(uv.y * slices + timeH * timeV * 3.0);
    float ns = steppedVal(fract(n  ),slices) + 2.0;
    float nsr = random1d(ns);
    vec2 uvn = uv;
    uvn.x += nsr * sin(timeH * TWO_PI + nsr * 20.0) * offset / textureSize(uInputTexture, 0).x;
    gl_FragColor = texture2D(uInputTexture, uvn);
}
