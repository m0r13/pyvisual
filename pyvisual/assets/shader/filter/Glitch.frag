#include <filter/basefilter.frag>

#include <lib/transform.glsl>

// Set the precision for data types used in this shader
precision highp float;
precision highp int;

// preprocessor bool dGlitchRGB; {"default" : true, "group" : "additional"}

uniform mat4 uTransformGlitch;
uniform float uStripeOffset; // {"default" : 1.0}
uniform float uStripeHeight; // {"default" : 1.0, "range" : [-1, 1]}

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
    vec4 outCol = frag;
    float maxOffset = amount/2.0;
    vec2 uvOff;
    for (float i = 0.0; i < 10.0; i += 1.0) {
        if (i > 10.0 * amount) break;
        
        float sliceY = random2d(vec2(sTime + amount, 2345.0 + float(i)));
        float sliceH = random2d(vec2(sTime + amount, 9035.0 + float(i))) * 0.25;
        float hOffset = randomRange(vec2(sTime + amount, 9625.0 + float(i)), -maxOffset, maxOffset);
        uvOff = uv;
        uvOff.x += hOffset * uStripeOffset;
        vec2 uvOff = fract(uvOff);

        // a and b are the limits for uv.y where a stripe with offseted texture occurs
        float a = sliceY;
        float b = fract(sliceY + sliceH);
        // this allows to make the stripes become thinner and disappear
        a = mix(a, (a+b) * 0.5, (1.0 - uStripeHeight) * 2.0);
        b = mix(b, (a+b) * 0.5, (1.0 - uStripeHeight) * 2.0);

        if (insideRange(fract(referenceUV.y), a, b) == 1.0 ){
            outCol = texture2D(uInputTexture, uvOff).rgba;
        }
    }
#if dGlitchRGB
    float maxColOffset = amount/6.0;
    vec2 colOffset = vec2(randomRange(vec2(sTime + amount, 3545.0),-maxColOffset,maxColOffset), randomRange(vec2(sTime , 7205.0),-maxColOffset,maxColOffset));
    uvOff = fract(uv + colOffset);
    float rnd = random2d(vec2(sTime + amount, 9545.0));
    if (rnd < 0.33){
        outCol.r = texture2D(uInputTexture, uvOff).r;
    }
    else if (rnd < 0.66) {
        outCol.g = texture2D(uInputTexture, uvOff).g;
    } else {
        outCol.b = texture2D(uInputTexture, uvOff).b;
    }
#endif
    return outCol;
}

