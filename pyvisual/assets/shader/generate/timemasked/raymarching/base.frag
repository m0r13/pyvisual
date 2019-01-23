#include <generate/timemasked/base.frag>

// uniforms

uniform float uScale; // {"default" : 1.0, "range" : [0.0001, Infinity]}

float scene(vec3 p);
vec4 sceneColor(vec3 p, vec3 n, float camDist, float convergence, vec4 bgColor);
vec4 backgroundColor(vec2 uv, float minD);

vec3 estimateSceneNormal(vec3 p) {
    vec3 eps = vec3(0.01, 0.0, 0.0);
    float nx = scene(p + eps.xyy) - scene(p - eps.xyy); 
    float ny = scene(p + eps.yxy) - scene(p - eps.yxy); 
    float nz = scene(p + eps.yyx) - scene(p - eps.yyx); 
    return normalize(vec3(nx, ny, nz));
}

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
    float lr = 0.8;

    int i = 0;
    float minD = 10000.0;
    for (; i < steps; i++) {
        dscene = scene(pos);
        minD = min(minD, dscene);
        if (abs(dscene) < epsilon) {
            break;
        }
        pos += rd*dscene * lr;
        dist += dscene * lr;
        lr = max(0.5, lr*0.85);
    }

    vec4 color = backgroundColor(uv, minD);
    if (dist < 100.0 && dscene < epsilon) {
        vec3 n = estimateSceneNormal(pos);
        color = sceneColor(pos, n, dist, float(i) / float(steps - 1), color);
    }

    pyvisualOutColor = color;
}

