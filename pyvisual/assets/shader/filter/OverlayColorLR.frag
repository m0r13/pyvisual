#include <filter/basefilter.frag>

uniform int uMode; // {"choices" : ["difference", "overlay", "grain merge", "exclusion", "hsv hue", "hsv saturation", "hsv value", "multiply", "multiply for mask"]}
uniform float uFactorLeft; // {"default" : 1.0, "range" : [0.0, 1.0]}
uniform float uFactorRight; // {"default" : 1.0, "range" : [0.0, 1.0]}
uniform vec4 uColor;

#include <lib/hsv.glsl>

vec4 filterFrag(vec2 uv, vec4 frag) {
    vec4 result;

    vec4 color = uColor;
    color.rgb *= uv.x < 0.5 ? uFactorLeft : uFactorRight;

    // TODO let's see if this case switch thing becomes a performance problem
    // can still optimize later
    if (uMode == 0) {
        result = abs(frag - color);
    } else if (uMode == 1) {
        result = mix(1.0 - 2.0 * (1.0 - frag) * (1.0 - color), 2.0 * frag * color, step(frag, vec4(0.5)));
    } else if (uMode == 2) {
        result = frag + color - vec4(0.5);
    } else if (uMode == 3) {
        result = frag + color - 2 * frag * color;
    } else if (uMode >= 4 && uMode <= 6) {
        vec3 hsvBG = rgb2hsv(frag.rgb);
        vec3 hsvFG = rgb2hsv(color.rgb);
        if (uMode == 4) {
            result.rgb = hsv2rgb(vec3(hsvFG.r, hsvBG.g, hsvBG.b));
        } else if (uMode == 5) {
            result.rgb = hsv2rgb(vec3(hsvBG.r, hsvFG.g, hsvBG.b));
        } else if (uMode == 6) {
            result.rgb = hsv2rgb(vec3(hsvBG.r, hsvBG.g, hsvFG.b));
        }
    } else if (uMode == 7) {
        result.rgb = frag.rgb * color.rgb;
    } else if (uMode == 8) {
        result.rgb = frag.rgb * color.rgb;
        frag.a *= frag.r;
    }
    return vec4(mix(frag.rgb, result.rgb, color.a), frag.a);
}
