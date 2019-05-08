#include <filter/basefilter.frag>

uniform float uStep; // {"default" : 1.0, "range" : [0.0, Infinity]}
uniform float uThreshold; // {"default" : 0.5, "range" : [0.0, Infinity]}
uniform float uSoftness; // {"default" : 0.1, "range" : [0.0, 0.5]}

float intensity(in vec4 color){
    //return sqrt((color.x*color.x)+(color.y*color.y)+(color.z*color.z));
    float i = length(color.rgb);
    return i;
}

vec4 filterFrag(vec2 uv, vec4 frag) {
    vec2 size = textureSize(uInputTexture, 0);
    float stepx = 1.0 / size.x * uStep;
    float stepy = 1.0 / size.y * uStep;

    float tleft = intensity(texture(uInputTexture,uv + vec2(-stepx,stepy)));
    float left = intensity(texture(uInputTexture,uv + vec2(-stepx,0)));
    float bleft = intensity(texture(uInputTexture,uv + vec2(-stepx,-stepy)));
    float top = intensity(texture(uInputTexture,uv + vec2(0,stepy)));
    float bottom = intensity(texture(uInputTexture,uv + vec2(0,-stepy)));
    float tright = intensity(texture(uInputTexture,uv + vec2(stepx,stepy)));
    float right = intensity(texture(uInputTexture,uv + vec2(stepx,0)));
    float bright = intensity(texture(uInputTexture,uv + vec2(stepx,-stepy)));

    float x = tleft + 2.0*left + bleft - tright - 2.0*right - bright;
    float y = -tleft - 2.0*top - tright + bleft + 2.0 * bottom + bright;
    float color = sqrt((x*x) + (y*y));

    return vec4(vec3(color), frag.a);
}

