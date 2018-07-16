#version 150

/**
* Example Fragment Shader
* Sets the color and alpha of the pixel by setting gl_FragColor
*/

// Set the precision for data types used in this shader
precision highp float;
precision highp int;

uniform float time;

uniform sampler2D uInputTexture;
uniform float amount;
uniform float speed;

in vec2 TexCoord0;

out vec4 oFragColor;

float random1d(float n){
    return fract(sin(n) * 43758.5453);
}
float random2d(vec2 n) {
    return fract(sin(dot(n, vec2(12.9898, 4.1414))) * 43758.5453);
}
float randomRange (in vec2 seed, in float min, in float max) {
    return min + random2d(seed) * (max - min);
}
float insideRange(float v, float bottom, float top) {
    return step(bottom, v) - step(top, v);
}
float rand(vec2 co){
    return fract(sin(dot(co.xy ,vec2(12.9898,78.233))) * 43758.5453);
}
void main() {
    vec2 uv = TexCoord0;
    float sTime = floor(time * speed * 6.0 * 24.0);
    vec3 inCol = texture2D(uInputTexture, uv).rgb;
    vec3 outCol = inCol;
    float maxOffset = amount/2.0;
    vec2 uvOff;
    for (float i = 0.0; i < 10.0; i += 1.0) {
        if (i > 10.0 * amount) break;
        
        float sliceY = random2d(vec2(sTime + amount, 2345.0 + float(i)));
        float sliceH = random2d(vec2(sTime + amount, 9035.0 + float(i))) * 0.25;
        float hOffset = randomRange(vec2(sTime + amount, 9625.0 + float(i)), -maxOffset, maxOffset);
        uvOff = uv;
        uvOff.x += hOffset;
        vec2 uvOff = fract(uvOff);
        if (insideRange(uv.y, sliceY, fract(sliceY+sliceH)) == 1.0 ){
            outCol = texture2D(uInputTexture, uvOff).rgb;
        }
    }
    float maxColOffset = amount/6.0;
    vec2 colOffset = vec2(randomRange(vec2(sTime + amount, 3545.0),-maxColOffset,maxColOffset), randomRange(vec2(sTime , 7205.0),-maxColOffset,maxColOffset));
    uvOff = fract(uv + colOffset);
    float rnd = random2d(vec2(sTime + amount, 9545.0));
    if (rnd < 0.33){
        outCol.r = texture2D(uInputTexture, uvOff).r;
    }else if (rnd < 0.66){
        outCol.g = texture2D(uInputTexture, uvOff).g;
    } else{
        outCol.b = texture2D(uInputTexture, uvOff).b;
    }
    outCol.rgb = vec3(max(max(outCol.r, outCol.g), outCol.b));
    gl_FragColor = vec4(outCol, texture2D(uInputTexture, uvOff).a);
}
