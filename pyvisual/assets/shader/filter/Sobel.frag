#include <filter/basefilter.frag>

// preprocessor bool dWithAlpha; {"default" : false, "group" : "additional"}

uniform float uStep; // {"default" : 1.0, "range" : [0.0, Infinity]}
uniform float uAlphaIntensity; // {"default" : 1.0, "range" : [0.0, Infinity]}
uniform vec4 uColor; // {"default" : [1.0, 1.0, 1.0, 1.0]}

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
    float edge = sqrt((x*x) + (y*y)) * frag.a;

#if dWithAlpha
    return vec4(uColor.rgb * edge, edge * uAlphaIntensity);
#else
    return vec4(uColor.rgb * edge * uAlphaIntensity, 1.0);
#endif
}

