#include <generate/timemasked/base.frag>

// uniforms

uniform float uScale; // {"default" : 1.0, "range" : [0.0001, Infinity]}

float scene(vec3 p);
vec4 sceneColor(vec3 p, vec3 n, float camDist, float convergence, vec4 bgColor);
vec4 backgroundColor(vec2 uv, float minD);

vec3 estimateSceneNormal(vec3 p) {
    /*
    vec2 e = vec2(0.01, 0.0);
    return normalize((vec3(scene(p+e.xyy), scene(p+e.yxy), scene(p+e.yyx)) - scene(p)) / e.x);
    */

    vec3 eps = vec3(0.01, 0.0, 0.0);
    float nx = scene(p + eps.xyy) - scene(p - eps.xyy); 
    float ny = scene(p + eps.yxy) - scene(p - eps.yxy); 
    float nz = scene(p + eps.yyx) - scene(p - eps.yyx); 
    return normalize(vec3(nx, ny, nz));
}

float rand(vec2 co) { return fract(sin(dot(co*0.123,vec2(12.9898,78.233))) * 43758.5453); }

uniform float uDitheringTime;

void generateFrag() {
    vec2 uv = 2.0*(vec2(pyvisualUV.x, 1.0 - pyvisualUV.y) * pyvisualResolution).xy/pyvisualResolution - 1.0; 
    uv.x *= pyvisualResolution.x/pyvisualResolution.y;

    vec3 ro = vec3(0.0, 0.0, 2.0); 
    vec3 rd = normalize(vec3(uv.x, uv.y, -1.4 * uScale)); 

    const int steps = 64;
    const float epsilon = 0.001;

    vec3 pos = ro; 
    float dist = 0.0;
    float dscene = 0.0;
    float lr = 1.0;

    int i = 0;
    float minD = 10000.0;

    //#define DITHER
    #ifdef DITHER
    vec2 dpos = ( (vec2(pyvisualUV.x, 1.0 - pyvisualUV.y) * pyvisualResolution).xy / pyvisualResolution.xy );
    vec2 num = vec2(1000.0);
    num.x *= pyvisualResolution.x / pyvisualResolution.y;
    vec2 seed = floor(dpos*num) / num + fract(uDitheringTime);
    #endif
    for (; i < steps; i++) {
        dscene = scene(pos);
        #ifdef DITHER
        dscene *= (0.25+0.5*rand(seed*vec2(i)));
        #endif 
        minD = min(minD, dscene);
        if (abs(dscene) < epsilon) {
            break;
        }
        pos += rd*dscene * lr;
        dist += dscene * lr;
        lr = max(0.5, lr*0.85);
    }

    vec4 color = backgroundColor(uv, 0.0);
    if (dist < 100.0) {
        vec3 n = estimateSceneNormal(pos);
        color = sceneColor(pos, n, dist, float(i) / float(steps - 1), color);
    }

    pyvisualOutColor = color;
}

