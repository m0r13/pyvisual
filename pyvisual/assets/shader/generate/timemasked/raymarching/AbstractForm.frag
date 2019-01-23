#include <generate/timemasked/raymarching/base.frag>

float sdSphere(vec3 p, float s) {
    return length(p)-s;
}

float sdBox(vec3 p, vec3 s) {
    return length(max(abs(p) - s, 0.0));
}

vec3 opRotateX(in vec3 p, float ang) {	
    return vec3(p.x, p.y*cos(ang) - p.z*sin(ang), p.y*sin(ang) + p.z*cos(ang)); 
}
vec3 opRotateY(in vec3 p, float ang) {	
    return vec3(p.x*cos(ang) - p.z*sin(ang), p.y, p.x*sin(ang) + p.z*cos(ang)); 
}
vec3 opRotateZ(in vec3 p, float ang) {	
    return vec3(p.x*cos(ang) - p.y*sin(ang), p.x*sin(ang) + p.y*cos(ang), p.z); 
}

vec2 opXYToPolar(vec2 xy) {
    vec2 texCoords = xy;

    float radius = length(texCoords);
    // this was an accident: interesting WTF
    // float angle = radians(atan(texCoords.y, texCoords.x)) + 3.141595;
    float angle = atan(texCoords.y, texCoords.x) + 3.141595;

    return vec2(angle, radius);
}

vec2 opPolarToXY(vec2 polar) {
    vec2 xy;
    xy.x = polar.y * cos(polar.x);
    xy.y = polar.y * sin(polar.x);
    //uv = (uv + vec2(1.0)) / 2.0;
    return xy;
}

vec2 opPolarMirror(vec2 polar, float n, float angleOffset) {
    float modAngle = radians(360.0) / n;
    polar.x = mod(polar.x + angleOffset, modAngle);
    if (polar.x > modAngle / 2) {
        polar.x = modAngle - polar.x;
    }
    return polar;
}

float opUnion( float d1, float d2 ) { return min(d1,d2); }

float opSubtraction( float d1, float d2 ) { return max(-d1,d2); }

float opIntersection( float d1, float d2 ) { return max(d1,d2); }

float opSmoothUnion( float d1, float d2, float k ) {
    float h = clamp( 0.5 + 0.5*(d2-d1)/k, 0.0, 1.0 );
    return mix( d2, d1, h ) - k*h*(1.0-h); }

float opSmoothSubtraction( float d1, float d2, float k ) {
    float h = clamp( 0.5 - 0.5*(d2+d1)/k, 0.0, 1.0 );
    return mix( d2, -d1, h ) + k*h*(1.0-h); }

float opSmoothIntersection( float d1, float d2, float k ) {
    float h = clamp( 0.5 - 0.5*(d2-d1)/k, 0.0, 1.0 );
    return mix( d2, d1, h ) + k*h*(1.0-h); }

uniform float uRotation;
uniform float uDisplace; // {"default" : 1.0, "range": [-1.0, 1.0]}
uniform float uMirrorRotation;

uniform float uSliceForm;
uniform float uSliceFormRotate;
uniform float uSliceColor;

uniform float uSliceTime; // {"default" : 1.5}
uniform float uSliceTimeOffset; // {"default" : 0.5}

uniform sampler2D uNoise;

#include <lib/noise3D.glsl>

float ditherOther(float color);

float scene(vec3 p) {

    /*
    //p = opRotateX(p, 0.3*uRotation);
    p = opRotateY(p, 0.2*uRotation);
    //p = opRotateZ(p, 0.4*uRotation);

    float noise = snoise(vec3(p.xy + vec2(pyvisualTime), p.z * 0.5 + pyvisualTime)) - 0.5;
    float b = sdBox(p, vec3(1.92, 1.0, 0.025 * 0.1));
    return opSmoothIntersection(b, noise, 0.1) + noise * 0.2;
    */

    /*
    p.y *= -1.0;
    p.y -= 4.2;

    vec3 c = vec3(5.0, 5.0, 5.0);
    if (p.y > 0.0) {

        p = mod(p,c)-0.5*c;
    }
    */

    p = opRotateX(p, 0.3*uRotation);
    p = opRotateY(p, 0.2*uRotation);
    p = opRotateZ(p, 0.4*uRotation);

    float mirrorRotation = uMirrorRotation * 0.1;
    p = opRotateX(p, 0.8 * mirrorRotation + 4.73);
    p = opRotateY(p, mirrorRotation);
    p = opRotateZ(p, -0.5 * mirrorRotation - 2.76);
    p.xz = opPolarToXY(opPolarMirror(opXYToPolar(p.xz), 8.0, -mirrorRotation));
    float timeOffset = p.y > uSliceTime ? uSliceTimeOffset : 0.0;
    p = opRotateY(p, uSliceFormRotate);

    vec3 pp = opRotateZ(p, mirrorRotation);
    float sliceFormBox = sdBox(pp, vec3(5.0, 5.0, uSliceForm)) - 0.05;
    sliceFormBox = opSmoothUnion(sliceFormBox, sdSphere(pp, 0.3), 0.1);
    //float sliceFormBox = sdBox(p - vec3(0.0, uSliceForm, 0.0), vec3(5.0, 0.01, 5.0)) - 0.05;
    //float sliceFormBox = -10000.0;
    //float timeOffset = 0.0;
    p = opRotateZ(p, -(-0.5 * mirrorRotation - 2.76));
    p = opRotateY(p, -mirrorRotation);
    p = opRotateX(p, -(0.8 * mirrorRotation + 4.73));

    float displace = clamp(sin((p.x+p.y+p.z)*20.0)*0.03, 0.0, 1.0) * uDisplace;
    float sphere = sdSphere(p, 0.5);
    float box = sdBox(p, vec3(0.5, 0.5, 0.5)) - 0.05;
    float time = sin(pyvisualTime * 0.2 + timeOffset);
    time = time * 0.75 - 0.5;
    float form = mix(box + displace, sphere, time);
    return opIntersection(form, sliceFormBox);
}

vec4 sceneColor(vec3 p, vec3 n, float camDist, float convergence, vec4 bgColor) {
    vec3 pp = p;
    pp = opRotateX(pp, 0.3*uRotation);
    pp = opRotateY(pp, 0.2*uRotation);
    pp = opRotateZ(pp, 0.4*uRotation);

    float mirrorRotation = uMirrorRotation * 0.1;
    pp = opRotateX(pp, 0.8 * mirrorRotation + 4.73);
    pp = opRotateY(pp, mirrorRotation);
    pp = opRotateZ(pp, -0.5 * mirrorRotation - 2.76);

    //vec3 pp = p;
    //pp = opRotateY(pp, 0.2*uRotation);

    float fr = 0.0, fg = 0.0, fb = 0.0;

    fr = pp.y < uSliceTime ? 1.0 : 0.0;
    //fr = ditherOther(snoise(vec3(pp.xy * 5.0, pyvisualTime)));
    //fr = 1.0;
    fg = 1.0 - fr;



    vec3 ro = vec3(0.0, 0.0, 2.0); 
    vec3 r = reflect(normalize(p - ro),n); 
    vec3 h = -normalize(n + p - ro); 
    float diff  = 1.0*clamp(dot(n, normalize(vec3(1,1,1))), 0.0, 1.0);
    //diff = 0.0;
    float diff2 = 0.2*clamp(dot(n, normalize(vec3(0.7,-1,0.5))), 0.0, 1.0);
    //diff2 = 0.0;
    float diff3 = 0.1*clamp(dot(n, normalize(vec3(-0.7,-0.4,0.7))), 0.0, 1.0);
    //diff3 = 0.0;
    float test = 1.0 * clamp(dot(n, normalize(vec3(1, 1, 1))), 0.0, 1.0);
    test = 0.0;
    float spec = pow(clamp(dot(h, normalize(vec3(1,1,1))), 0.0, 1.0), 50.0); 
    float amb = 0.2 + p.y; 
    vec3 cubeColor = test*vec3(1,0,0) + diff*vec3(1,1,1) + diff2*vec3(fr,fg,fb)  + diff3*vec3(fr,fg,1) + spec*vec3(1,1,1)  + amb*vec3(0.2,0.2,0.2);
    cubeColor *= (1.0 - convergence);
    //cubeColor /= camDist;
    // count of iterations until convergance as color
    //cubeColor = mix(vec3(1.0, 0.0, 0.0), vec3(0.0, 1.0, 0.0), step(8.0, float(i)));
    // normal as color
    //cubeColor = clamp(dot(n, normalize(vec3(1,1,1))), 0.0, 1.0) * (n + vec3(1.0)) / 2.0 + spec*vec3(1,1,1)  + amb*vec3(0.2,0.2,0.2);
    //dist = clamp(dist, 0.0, 1.0) / 1.0;
    //cubeColor = mix(vec3(1.0, 0.0, 0.0), vec3(0.0, 1.0, 0.0), dist);
    return mix(bgColor, vec4(cubeColor, 1.0), 1.0);
}

const int indexMatrix8[64] = int[](0,  32, 8,  40, 2,  34, 10, 42,
                                     48, 16, 56, 24, 50, 18, 58, 26,
                                     12, 44, 4,  36, 14, 46, 6,  38,
                                     60, 28, 52, 20, 62, 30, 54, 22,
                                     3,  35, 11, 43, 1,  33, 9,  41,
                                     51, 19, 59, 27, 49, 17, 57, 25,
                                     15, 47, 7,  39, 13, 45, 5,  37,
                                     63, 31, 55, 23, 61, 29, 53, 21);

float indexValue() {
    int x = int(mod(gl_FragCoord.x * 0.5, 8));
    int y = int(mod(gl_FragCoord.y * 0.5, 8));
    return indexMatrix8[(x + y * 8)] / 64.0;
}

vec3 ditherGreen(float color) {
    float closestColor = (color < 0.5) ? 0 : 1;
    float secondClosestColor = 1 - closestColor;
    float d = indexValue();
    float distance = abs(closestColor - color);
    float c = (distance < d) ? closestColor : secondClosestColor;
    return vec3(0.0, 0.75*c * ((1.0-pow(1.0-color,1.5)) * 3.0) + 0.0, 0.0);
}

float ditherOther(float color) {
    float closestColor = (color < 0.5) ? 0 : 1;
    float secondClosestColor = 1 - closestColor;
    float d = indexValue();
    float distance = abs(closestColor - color);
    float c = (distance < d) ? closestColor : secondClosestColor;
    return 0.75*c * ((1.0-pow(1.0-color,1.5)) * 3.0);
}

vec4 backgroundColor(vec2 uv, float minD) {
    const float glowMaxDist = 0.5;
    const float glowExp = 0.2;

    float d = min(glowMaxDist, minD) / glowMaxDist;

    float c = (1.0 - length(uv * 1.2)) * 0.25;
    //vec3 color = vec3(ditherGreen(c));
    vec3 color = vec3(c);
    //uv *= 0.2;
    //float noise = texture2D(uNoise, uv).r;
    //color.rgb += mix(-20.5/255.0, 20.5/255.0, noise) * 0.05;
    //return vec4(uv.x, 0.0, 0.0, 1.0);

    //color = 1.0 - ((1.0 - color) * pow(d, glowExp));
    return vec4(color, 1.0);
}

