#include <generate/timemasked/base.frag>

#include <lib/noise3D.glsl>

float sdCircle(vec2 p, float r) {
  return length(p) - r;
}

float sdBox( in vec2 p, in vec2 b ) {
    vec2 d = abs(p)-b;
    return length(max(d,vec2(0))) + min(max(d.x,d.y),0.0);
}

float sdBox3( in vec3 p, in vec3 b ) {
    vec3 d = abs(p)-b;
    return length(max(d,vec3(0))) + min(max(d.x,d.y),0.0);
}
float sdSphere3(vec3 p, float s) {
    return length(p)-s;
}

vec3 opRotate3(vec3 p, vec3 angles) {
    vec3 c = cos(angles);
    vec3 s = sin(angles);

    p = vec3(p.x, p.y*c.x - p.z*s.x, p.y*s.x + p.z*c.x);
    p = vec3(p.x*c.y - p.z*s.y, p.y, p.x*s.y + p.z*c.y);
    p = vec3(p.x*c.z - p.y*s.z, p.x*s.z + p.y*c.z, p.z);
    return p;

    /*
    mat3 rotX = mat3( 1.0, 0.0, 0.0, 0.0,c.x,s.x, 0.0,-s.x, c.x);
    mat3 rotY = mat3( c.y, 0.0,-s.y, 0.0,1.0,0.0, s.y, 0.0, c.y);
    mat3 rotZ = mat3( c.z, s.z, 0.0,-s.z,c.z,0.0, 0.0, 0.0, 1.0);
    return p*(rotX*rotY*rotZ);
    */
}

vec2 opRotateZ(in vec2 p, float ang) {
    float cosa = cos(ang);
    float sina = sin(ang);
    return vec2(p.x*cosa - p.y*sina, p.x*sina + p.y*cosa); 
}

float opAnnular(float d, float r) {
    return abs(d) - r;
}

float opSmoothUnion( float d1, float d2, float k ) {
    float h = clamp( 0.5 + 0.5*(d2-d1)/k, 0.0, 1.0 );
    return mix( d2, d1, h ) - k*h*(1.0-h); }

float opSmoothSubtraction( float d1, float d2, float k ) {
    float h = clamp( 0.5 - 0.5*(d2+d1)/k, 0.0, 1.0 );
    return mix( d2, -d1, h ) + k*h*(1.0-h); }

float opSmoothIntersection( float d1, float d2, float k ) {
    float h = clamp( 0.5 - 0.5*(d2-d1)/k, 0.0, 1.0 );
    return mix( d2, d1, h ) + k*h*(1.0-h); }

float v;

uniform float uNoiseScale; // {"default" : 1.0, "range" : [0.0, Infinity]}
uniform float uNoiseOffset; // {"default" : 0.0}
uniform float uDisplaceScale; // {"default" : 1.0}

uniform float uMaskScale; // {"default" : 1.0}
uniform float uAlpha; // {"default" : 1.0}

float scene(vec2 p) {
    /*
    float xoff = sin(pyvisualTime);
    float circle = sdCircle(p + vec2(xoff, -0.35), 0.5);
    float box = sdBox(p + vec2(-xoff, 0.35), vec2(0.5)) - 0.01;
    return opSmoothUnion(circle, box, 0.25);
    */

    /*
    float box = sdBox(opRotateZ(p, pyvisualTime + 3.14159*0.25), vec2(0.5));
    return opAnnular(box, 0.05);
    */

    /*
    float xoff = pyvisualTime * 1.0;
    float yoff = sin(pyvisualTime) * 0.5;
    vec2 c = vec2(3.0);
    p *= 3.0;
    vec2 q0 = mod(p + vec2(xoff, yoff), c) - 0.5*c;
    vec2 q1 = mod(p + vec2(-xoff, -yoff), c) - 0.5*c;
    q0.y = p.y + yoff;
    q1.y = p.y - yoff;
    float circle = sdCircle(q0 + vec2(0.5, 0.75), 0.75);
    float box = sdBox(q1 + vec2(0.0, -0.75), vec2(0.75));
    return opSmoothUnion(circle, box, 0.25);
    */

    /*
    float cut = sin(pyvisualTime) * 0.5 * 0.0;
    vec3 pp = vec3(p, cut);
    pp = opRotate3(pp, vec3(0.2, 0.3, 0.4) * pyvisualTime * 0.2 * vec3(1.0, 1.0, 1.0));
    float displace = clamp(sin((pp.x+pp.y+pp.z)*20.0)*0.03, 0.0, 1.0) * 5.0;
    float box = sdBox3(pp, vec3(0.5));
    float sphere = sdSphere3(pp, 0.5);
    v = pp.y;
    return box;
    */

    /*
    float time = sin(pyvisualTime * 0.2);
    time = time * 0.75 - 0.5;
    float form = mix(box + displace, sphere, time);
    return form;
    */

    //v = 1.0;

    float t = uMaskScale * uMaskScale;
    float circle = sdCircle(p, 0.6 * 1.0 / t);

    vec2 perlinP = p;
    // version 1: use position as noise position
    //perlinP *= uNoiseScale;
    // version 2: offsets are along a circle in the noise space (depending on polar angle of position)
    float angle = atan(p.y, p.x);
    perlinP = vec2(sin(angle + uNoiseOffset), cos(angle + uNoiseOffset)) * uNoiseScale;

    float noise = snoise(vec3(perlinP, pyvisualTime));

    float amplitude = 0.2 * noise * uDisplaceScale;
    // triangle waveform offset, not so much (yet)e;
    //float period = 3.14159 / 3.0;
    //float displace = (2*amplitude) / period * abs(mod(angle, period) - period/2.0) * 2.0 - (2*amplitude) / 4.0;
    float displace = sin(angle * 6.0) * amplitude;

    // two versions here also possible
    // - multiply noise by sin/triangle/etc. waveform (seems nicer for now)
    // - just take noise as offset
    return circle + displace * t;
}

void generateFrag() {
    vec2 uv = 2.0*(vec2(pyvisualUV.x, 1.0 - pyvisualUV.y) * pyvisualResolution).xy/pyvisualResolution - 1.0; 
    uv.x *= pyvisualResolution.x/pyvisualResolution.y;

    float d = scene(uv);
    float value = 1.0 - smoothstep(0.0, 0.02, d);
    value *= smoothstep(-0.5, 0.0, v) * (1.0-smoothstep(0.0, 0.5, v));

    pyvisualOutColor = vec4(vec3(value * uAlpha), 1.0);
}

