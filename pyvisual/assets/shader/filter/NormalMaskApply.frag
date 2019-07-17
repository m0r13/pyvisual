#include <filter/basefilter.frag>

// preprocessor bool dTransparent; // {"default" : false, "group" : "additional"}

uniform sampler2D uForeground;
uniform sampler2D uMask;

uniform bool uSwitch;

vec4 filterFrag(vec2 uv, vec4 frag) {
    vec4 mask = texture2D(uMask, uv);
    vec4 fg = texture2D(uForeground, uv);
    vec4 bg = frag;

#if dTransparent
    //return mix(bg, fg, mask.r * mask.a);
#else
    if (mask.a > 0.0) {
        float value = mask.r;
        vec4 f = uSwitch ? bg : fg;
        return vec4(f.rgb * value, f.a);
    }

    return uSwitch ? fg : bg;
#endif
}
