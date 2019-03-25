#include <generate/timemasked/raymarching/base.frag>

float sdSphere(vec3 p, float s) {
    return length(p)-s;
}

float sdBox(vec3 p, vec3 s) {
    return length(max(abs(p) - s, 0.0));
}

float sdTriPrism( vec3 p, vec2 h ) {
    vec3 q = abs(p);
    return max(q.z-h.y,max(q.x*0.866025+p.y*0.5,-p.y)-h.x*0.5);
}

float sdOctahedron( in vec3 p, in float s) {
    p = abs(p);
    return (p.x+p.y+p.z-s)*0.57735027;
}

/*
float sdOctahedron( in vec3 p, in float s)
{
    p = abs(p);
    float m = p.x+p.y+p.z-s;
    vec3 q;
         if( 3.0*p.x < m ) q = p.xyz;
    else if( 3.0*p.y < m ) q = p.yzx;
    else if( 3.0*p.z < m ) q = p.zxy;
    else return m*0.57735027;
    
    float k = clamp(0.5*(q.z-q.y+s),0.0,s); 
    return length(vec3(q.x,q.y-s+k,q.z-k)); 
}
*/

float sdTorus( vec3 p, vec2 t )
{
  vec2 q = vec2(length(p.xz)-t.x,p.y);
  return length(q)-t.y;
}

vec3 opRotateX(in vec3 p, float ang) {
    float cosa = cos(ang);
    float sina = sin(ang);
    return vec3(p.x, p.y*cosa - p.z*sina, p.y*sina + p.z*cosa);
}
vec3 opRotateY(in vec3 p, float ang) {
    float cosa = cos(ang);
    float sina = sin(ang);
    return vec3(p.x*cosa - p.z*sina, p.y, p.x*sina + p.z*cosa); 
}
vec3 opRotateZ(in vec3 p, float ang) {
    float cosa = cos(ang);
    float sina = sin(ang);
    return vec3(p.x*cosa - p.y*sina, p.x*sina + p.y*cosa, p.z); 
}

vec3 opRotate(vec3 p, vec3 angles) {
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

vec3 opRotateInv(vec3 p, vec3 angles) {
    vec3 c = cos(-angles);
    vec3 s = sin(-angles);

    p = vec3(p.x*c.z - p.y*s.z, p.x*s.z + p.y*c.z, p.z);
    p = vec3(p.x*c.y - p.z*s.y, p.y, p.x*s.y + p.z*c.y);
    p = vec3(p.x, p.y*c.x - p.z*s.x, p.y*s.x + p.z*c.x);
    return p;

    /*
    mat3 rotX = mat3( 1.0, 0.0, 0.0, 0.0,c.x,s.x, 0.0,-s.x, c.x);
    mat3 rotY = mat3( c.y, 0.0,-s.y, 0.0,1.0,0.0, s.y, 0.0, c.y);
    mat3 rotZ = mat3( c.z, s.z, 0.0,-s.z,c.z,0.0, 0.0, 0.0, 1.0);
    return p*(rotZ*rotY*rotX);
    */
}


/*
vec3 opRotate(vec3 p, vec3 axis, float angle)
{
    axis = normalize(axis);
    float s = sin(angle);
    float c = cos(angle);
    float oc = 1.0 - c;

    return p*mat3(oc * axis.x * axis.x + c,           oc * axis.x * axis.y - axis.z * s,  oc * axis.z * axis.x + axis.y * s,
                oc * axis.x * axis.y + axis.z * s,  oc * axis.y * axis.y + c,           oc * axis.y * axis.z - axis.x * s,
                oc * axis.z * axis.x - axis.y * s,  oc * axis.y * axis.z + axis.x * s,  oc * axis.z * axis.z + c);
}
*/

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
uniform float uAlpha; // {"default" : 1.0}
uniform float uAlphaFactor; // {"default" : 1.0}

// mirroring enabled, but uMirrorCount == 0.0 should be as mirroring disabled
// both looks and performance
#define MIRROR

float scene(vec3 p) {
    /*
    p = opRotateX(p, 0.3*uRotation);
    p = opRotateY(p, 0.2*uRotation);
    p = opRotateZ(p, 0.4*uRotation);
    */
    p = opRotate(p, vec3(0.3, 0.05, 0.4) * uRotation * vec3(1.5, 1.0, 1.0));

    float testBox = sdBox(p, vec3(0.25));
    float testPrism = sdTriPrism(p, vec2(0.5, 0.3));
    float octa = sdOctahedron(p, 0.5);
    float torus = sdTorus(p, vec2(0.4, 0.015 * 5.0));

    float time = sin(pyvisualTime * 0.1);
    // alpha from -0.5 to 1.5
    float alpha = time + 0.5;
    float test = mix(octa, testPrism, alpha);
    
    return test;
}

vec3 estimateSceneNormal(vec3 p) {
    //vec2 e = vec2(0.01, 0.0);
    //return normalize((vec3(scene(p+e.xyy), scene(p+e.yxy), scene(p+e.yyx)) - scene(p)) / e.x);

    vec3 eps = vec3(0.01, 0.0, 0.0);
    float nx = scene(p + eps.xyy) - scene(p - eps.xyy); 
    float ny = scene(p + eps.yxy) - scene(p - eps.yxy); 
    float nz = scene(p + eps.yyx) - scene(p - eps.yyx); 
    return normalize(vec3(nx, ny, nz));
}

vec4 sceneColor(vec3 p, float camDist, vec4 bgColor) {
    vec3 n = estimateSceneNormal(p);
    vec3 ro = vec3(0.0, 0.0, 2.0); 
    vec3 r = reflect(normalize(p - ro),n); 
    vec3 h = -normalize(n + p - ro);
    return vec4(vec3(pow(dot(n, normalize(vec3(1, 1, 1))), 1.0) * 0.7 + 0.3) * uAlpha * uAlphaFactor, 1.0);
}

vec4 backgroundColor(vec2 uv) {
    return vec4(vec3(0.0), 1.0);
    return vec4((1.0 - vec3(length(uv*0.5)))*0.2, 1.0);
}

