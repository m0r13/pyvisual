// uInputTexture is (still) built-in to Shader class
uniform sampler2D uInputTexture; // {"skip" : true, "alias" : "input"}

// alias these inputs as they are "built-in" into the filter nodes
// and should appear different from the other uniform inputs
uniform sampler2D uFilterMaskTexture; // {"alias" : "filter_mask"}
uniform float uFilterMaskFactor; // {"alias" : "mask_factor", "default" : 1.0}
uniform int uFilterMaskMode; // {"alias" : "filter_mode", "default" : 2, "choices" : ["input", "mask", "filtered", "input_filtered_masked", "input_masked", "filtered_masked"]}
uniform vec4 uFilterBackgroundColor; // {"alias" : "filter_bg", "default" : [0.0, 0.0, 0.0, 0.0]}

in vec2 TexCoordi;
in vec2 TexCoord0;
out vec4 oFragColor;

vec4 filterFrag(vec2, vec4);

void main( ) {
#if defined(DONT_SAMPLE_FRAGMENT) && !defined(ADVANCED_FILTERING)
    // slight performance hack:
    // some shaders right away sample another fragment
    // so we don't need to sample the fragment at original uv
    // in case no advanced filtering/masking is enabled
    vec4 frag = vec4(0.0);
#else
    vec4 frag = texture2D(uInputTexture, TexCoord0);
#endif
    vec4 fragFiltered = filterFrag(TexCoord0, frag);

#ifdef ADVANCED_FILTERING
    float mask = texture2D(uFilterMaskTexture, TexCoord0).r * uFilterMaskFactor;

    if (uFilterMaskMode == 0) {
        // only input
        oFragColor = frag;
    } else if (uFilterMaskMode == 1) {
        // only mask
        oFragColor = vec4(vec3(mask), 1.0);
    } else if (uFilterMaskMode == 2) {
        // only filtered
        oFragColor = fragFiltered;
    } else if (uFilterMaskMode == 3) {
        // only filtered where mask, otherwise input
        oFragColor = mix(frag, fragFiltered, mask);
    } else if (uFilterMaskMode == 4) {
        // input where mask, otherwise background, interpolated in-between
        oFragColor = mix(uFilterBackgroundColor, frag, mask);
    } else if (uFilterMaskMode == 5) {
        // filtered where mask, otherwise background, interpolated in-between
        oFragColor = mix(uFilterBackgroundColor, fragFiltered, mask);
    }
#else
    oFragColor = fragFiltered;
#endif
}

