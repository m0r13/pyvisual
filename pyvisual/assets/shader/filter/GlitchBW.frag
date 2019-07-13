#include <filter/basefilter.frag>

#include <lib/transform.glsl>

// Set the precision for data types used in this shader
precision highp float;
precision highp int;

uniform mat4 uTransformGlitch;

uniform float time;
uniform float amount;
uniform float speed;

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

vec4 filterFrag(vec2 uv, vec4 frag) {
    vec2 referenceUV = transformUV(uv, uTransformGlitch, textureSize(uInputTexture, 0));

    float sTime = floor(time * speed * 6.0 * 24.0);
    vec3 inCol = frag.rgb;
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
        if (insideRange(fract(referenceUV.y), sliceY, fract(sliceY+sliceH)) == 1.0 ){
            outCol = texture2D(uInputTexture, uvOff).rgb;
        }
    }
    float maxColOffset = amount/6.0;
    vec2 colOffset = vec2(randomRange(vec2(sTime + amount, 3545.0),-maxColOffset,maxColOffset), randomRange(vec2(sTime , 7205.0),-maxColOffset,maxColOffset));
    uvOff = fract(uv + colOffset);
    float rnd = random2d(vec2(sTime + amount, 9545.0));
    if (rnd < 0.33){
        outCol.rgb = texture2D(uInputTexture, uvOff).rgb;
    } /* else if (rnd < 0.66){
        outCol.g = texture2D(uInputTexture, uvOff).g;
    } else{
        outCol.b = texture2D(uInputTexture, uvOff).b;
    }
    */
    return vec4(outCol,1.0);
}

