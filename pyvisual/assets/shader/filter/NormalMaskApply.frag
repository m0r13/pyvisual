#include <filter/basefilter.frag>

// preprocessor bool dTransparent; // {"default" : false, "group" : "additional"}

uniform sampler2D uForeground;
uniform sampler2D uMask;
uniform float uAlpha; // {"default" : 1.0}

uniform bool uSwitch;

vec4 filterFrag(vec2 uv, vec4 frag) {
    vec4 mask = texture2D(uMask, uv);
    vec4 fg = texture2D(uForeground, uv);
    vec4 bg = frag;

#if dTransparent
    //return mix(bg, fg, mask.r * mask.a);
#else
    vec4 fg_result;
    vec4 bg_result = uSwitch ? fg : bg;
    if (mask.a > 0.0) {
        float value = mask.r;
        vec4 f = uSwitch ? bg : fg;
        fg_result = vec4(f.rgb * value, f.a);
        //return fg_result;
    } else {
        fg_result = bg_result;
    }

    //return bg_result;
    return mix(bg_result, fg_result, uAlpha);
#endif
}
