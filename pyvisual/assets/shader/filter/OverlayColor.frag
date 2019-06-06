#include <filter/basefilter.frag>

uniform int uMode; // {"choices" : ["difference", "overlay", "grain merge", "exclusion", "hsv hue", "hsv saturation", "hsv value", "multiply"]}
uniform vec4 uColor;

#include <lib/hsv.glsl>

vec4 filterFrag(vec2 uv, vec4 frag) {
    vec4 result;

    // TODO let's see if this case switch thing becomes a performance problem
    // can still optimize later
    if (uMode == 0) {
        result = abs(frag - uColor);
    } else if (uMode == 1) {
        result = mix(1.0 - 2.0 * (1.0 - frag) * (1.0 - uColor), 2.0 * frag * uColor, step(frag, vec4(0.5)));
    } else if (uMode == 2) {
        result = frag + uColor - vec4(0.5);
    } else if (uMode == 3) {
        result = frag + uColor - 2 * frag * uColor;
    } else if (uMode >= 4 && uMode <= 6) {
        vec3 hsvBG = rgb2hsv(frag.rgb);
        vec3 hsvFG = rgb2hsv(uColor.rgb);
        if (uMode == 4) {
            result.rgb = hsv2rgb(vec3(hsvFG.r, hsvBG.g, hsvBG.b));
        } else if (uMode == 5) {
            result.rgb = hsv2rgb(vec3(hsvBG.r, hsvFG.g, hsvBG.b));
        } else if (uMode == 6) {
            result.rgb = hsv2rgb(vec3(hsvBG.r, hsvBG.g, hsvFG.b));
        }
    } else if (uMode == 7) {
        result.rgb = frag.rgb * uColor.rgb;
    }
    return vec4(mix(frag.rgb, result.rgb, uColor.a), frag.a);
}
