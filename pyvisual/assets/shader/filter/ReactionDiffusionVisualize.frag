#include <filter/basefilter.frag>

vec4 filterFrag(vec2 uv, vec4 frag) {
    vec2 size = textureSize(uInputTexture, 0);

    // Read in the blurred pixel value. There's no rule that says you can't read in the
    // value in the "X" channel, but blurred stuff is easier to bump, that's all.
    float c = 1. - texture2D(uInputTexture, uv).y; 
    // Reading in the same at a slightly offsetted position. The difference between
    // "c2" and "c" is used to provide the highlighting.
    float c2 = 1. - texture2D(uInputTexture, uv + .5 / size.xy).y;
    

    // Color the pixel by mixing two colors in a sinusoidal kind of pattern.
    //
    float pattern = -cos(uv.x*0.75*3.14159-0.9)*cos(uv.y*1.5*3.14159-0.75)*0.5 + 0.5;
    //
    // Blue and gold, for an abstract sky over a... wheat field look. Very artsy. :)
    vec3 col = vec3(c*1.5, pow(c, 2.25), pow(c, 6.));
    col = mix(col, col.zyx, clamp(pattern-.2, 0., 1.) );
    
    // Extra color variations.
    //vec3 col = mix(vec3(c*1.2, pow(c, 8.), pow(c, 2.)), vec3(c*1.3, pow(c, 2.), pow(c, 10.)), pattern );
	//vec3 col = mix(vec3(c*1.3, c*c, pow(c, 10.)), vec3(c*c*c, c*sqrt(c), c), pattern );
    
    // Adding the highlighting. Not as nice as bump mapping, but still pretty effective.
    col += vec3(.6, .85, 1.)*max(c2*c2 - c*c, 0.)*12.;

    // Apply a vignette and increase the brightness for that fake spotlight effect.
    col *= pow( 16.0*uv.x*uv.y*(1.0-uv.x)*(1.0-uv.y) , .125)*1.15;
    
    // Fade in for the first few seconds.
    //col *= smoothstep(0., 1., iTime/2.);

    // Done.
    return vec4(min(col, 1.), 1.); 
}
