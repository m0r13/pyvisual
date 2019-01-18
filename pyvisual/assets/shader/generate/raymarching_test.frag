#include <generate/base_raymarching.frag>

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

uniform float uTest;
const int Iterations = 15;
float Scale = uTest;
const float FoldingLimit = 100.0;
/* Camera at z-16
const int Iterations = 8;
const float Scale = 2.0;
const float FoldingLimit = 10000.0;
const float MinRad2 = 0.25;
*/
float MandleBox(vec3 pos) {
   float MinRad2 = 0.15 + abs(sin(pyvisualTime*.25))*.75;
   vec4 scale = vec4(Scale, Scale, Scale, abs(Scale)) / MinRad2;
   float AbsScalem1 = abs(Scale - 1.0);
   float AbsScaleRaisedTo1mIters = pow(abs(Scale), float(1-Iterations));
   vec4 p = vec4(pos,1.0), p0 = p;  // p.w is the distance estimate
   
   for (int i=0; i<Iterations; i++)
   {
      p.xyz = clamp(p.xyz, -1.0, 1.0) * 2.0 - p.xyz;
      float r2 = dot(p.xyz, p.xyz);
      p *= clamp(max(MinRad2/r2, MinRad2), 0.0, 1.0);
      p = p*scale + p0;
      if (r2>FoldingLimit) break;
   }
   return ((length(p.xyz) - AbsScalem1) / p.w - AbsScaleRaisedTo1mIters);
}

uniform float uPower;
uniform float uForm;

float scene(vec3 p) {
    p = opRotateY(p, pyvisualTime * 0.1);

    return opIntersection(sdBox(p, vec3(1.0)), MandleBox(p));
    /*
    const int Iterations = 6;
    const float Bailout = 2.0;
    vec3 z = p;
    float dr = 1.0;
    float r = 0.0;
    for (int i = 0; i < Iterations ; i++) {
        r = length(z);
        if (r>Bailout) break;

        // convert to polar coordinates
        float theta = acos(z.z/r);
        float phi = atan(z.y,z.x);
        dr =  pow( r, uPower-1.0)*uPower*dr + 1.0;

        // scale and rotate the point
        float zr = pow( r,uPower);
        theta = theta*uPower;
        phi = phi*uPower;

        // convert back to cartesian coordinates
        z = zr*vec3(sin(theta)*cos(phi), sin(phi)*sin(theta), cos(theta));
        z+=p;
    }
    return 0.5*log(r)*r/dr;
    */

    float r = length(p);
    float dr = 1.0;

    // convert to polar coordinates
    float theta = acos(p.z/r);
    float phi = atan(p.y,p.x);
    //dr =  pow( r, uPower-1.0)*uPower*dr + 1.0;

    // scale and rotate the point
    float zr = pow( r,uPower);
    theta = theta*uPower;
    phi = phi*uPower;

    /*
    theta = theta * uTest;
    phi = phi * uTest;
    */

    // convert back to cartesian coordinates
    p = zr*vec3(sin(theta)*cos(phi), sin(phi)*sin(theta), cos(theta));

    float sphere = sdSphere(p, 0.5);
    float box = sdBox(p, vec3(0.5, 0.5, 0.5)) - 0.05;
    //return opSmoothUnion(box, sphere, 0.25);
    return mix(box, sphere, sin(uForm * 0.2));
}

vec4 sceneColor(vec3 p, vec3 n, float camDist, float convergence, vec4 bgColor) {
    vec3 ro = vec3(0.0, 0.0, 2.0); 
    vec3 r = reflect(normalize(p - ro),n); 
    vec3 h = -normalize(n + p - ro); 
    float diff  = 1.0*clamp(dot(n, normalize(vec3(1,1,1))), 0.0, 1.0); 
    float diff2 = 0.2*clamp(dot(n, normalize(vec3(0.7,-1,0.5))), 0.0, 1.0); 
    float diff3 = 0.1*clamp(dot(n, normalize(vec3(-0.7,-0.4,0.7))), 0.0, 1.0); 
    float spec = pow(clamp(dot(h, normalize(vec3(1,1,1))), 0.0, 1.0), 50.0); 
    float amb = 0.2 + p.y; 
    vec3 cubeColor = diff*vec3(1,1,1) + diff2*vec3(1,0,0)  + diff3*vec3(1,0,1) + spec*vec3(1,1,1)  + amb*vec3(0.2,0.2,0.2);
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

vec4 backgroundColor(vec2 uv, float minD) {
    const float glowMaxDist = 0.5;
    const float glowExp = 0.2;

    float d = min(glowMaxDist, minD) / glowMaxDist;

    vec3 color = vec3(1.0 - length(uv * 0.5)) * 0.2;
    //color = 1.0 - ((1.0 - color) * pow(d, glowExp));
    return vec4(color, 1.0);
}

