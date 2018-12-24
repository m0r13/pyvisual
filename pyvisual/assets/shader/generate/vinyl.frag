#include <generate/base_time_mask.frag>

uniform float uBrightness; // {"default" : 0.5}
uniform float uInvert; // {"default" : 0.0, "range" : [0.0, 1.0]}
uniform float uTheta;

uniform float uLightTheta;
uniform float uLightScale; // {"default" : 1.0}

#include <lib/noise2D.glsl>

const float PI = 3.1415952;

float random1D(float x) {
    return fract(sin(x) * 43758.5453123);
}

float fbm1(vec2 p) {
    const int octaves = 4;
    float gain = 0.75;
    float lacunarity = 2.0;
    
    float f = 0.0;
    float frequency = 1.0;
    float amplitude = 0.5;
    for (int i = 0; i < octaves; i++) {
        f += snoise(p * frequency) * amplitude;
        amplitude *= gain;
        frequency *= lacunarity + float(i) / 100.0;
    }
    return min(1.0, f);
}

float fbm2(vec2 p) {
    const int octaves = 4;
    float gain = 0.9;
    float lacunarity = 2.0;
    
    float f = 0.0;
    float frequency = 1.0;
    float amplitude = 0.5;
    for (int i = 0; i < octaves; i++) {
        f += snoise(p * frequency) * amplitude;
        amplitude *= gain;
        frequency *= lacunarity + float(i) / 100.0;
    }
    return min(1.0, f);
}

float to01(float theta) {
    return (theta + PI) / (2.0 * PI);
}

float to2pi(float theta) {
    return theta * 2.0 * PI - PI;
}

float norm(float theta) {
    return to2pi(mod(to01(theta), 1.0));
}

void generateFrag() {
    // TODO this code is horrible
    // correct it once I'm able to
    const float smoothness = 0.005;
    const float start = 0.2;
    const float leadin_groove = 0.25;
    const float main = 0.4;
    const float leadout_groove = 0.98;

    vec2 uv = pyvisualUV - vec2(0.5);
    vec2 resolution = textureSize(uInputTexture, 0);
    uv.x *= resolution.x / resolution.y;

    // distance from center
    float d = length(uv) * 2.0;

    // TODO make smooth borders properly
    //float v = 1.0 - smoothstep(1.0 - smoothness, 1.0, d);
    //v *= smoothstep(leadin_groove, leadin_groove + 0.005, d);
    float v = 1.0 - step(1.0, d);
    v *= step(leadin_groove, d);

    if ((d < main || d > leadout_groove) && v > leadin_groove && v < 1.0) {
        v = 0.0;
    }

    if (v > 0.001) {
        // was 0.2
        v = uBrightness;

        float dd = d - mod(d, 1.0 / 250.0);
        float ddd = d - mod(d, 1.0 / 50.0);
        // this makes leadin/out groove have one brightness each without noise
        vec2 p = vec2(clamp(d, main, leadout_groove) + pyvisualTime * 0.1, 0.0);
        float noise = fbm1(p);
        // was 0.5 - 1.0
        v *= mix(0.5, 1.0, noise);

        // somehow it looks cooler with + instead of -
        //v *= mix(0.8, 1.0, noise + mod(noise, 0.2));

        float U = 2*PI*dd;
        // in [-pi, pi]
        float theta = atan(uv.y, uv.x);
        // now in [0, 1]
        theta = (theta + PI) / (2.0*PI);
        theta = mod(theta + uTheta, 1.0);
        if (theta > 0.5) {
            theta = 1.0 - theta;
        }

        float randomOffset = random1D(dd * 1.0);
        float grooveDist = theta * U;
        float groovePosition = randomOffset + grooveDist * 0.1;
        vec2 pGroove = vec2(ddd * 4.8, mod(groovePosition * 100.0, 5.0));
        float grooveRandom = snoise(pGroove);

        float steps = 2.0;
        float grooveNoise = grooveRandom - mod(grooveRandom, 1.0 / steps);

        //v = grooveNoise;
        // was 0.8 - 1.0
        v *= mix(0.6, 0.8, grooveRandom);

        float actualTheta = norm(atan(uv.y, uv.x));
        float lightTheta = uLightTheta;
        vec2 pLight = vec2(d * 4.8, lightTheta * 2.0);
        float lightchange = fbm2(pLight);

        v += pow(1.0 - smoothstep(0, mix(0.25, 0.4, lightchange) * uLightScale, abs(norm(actualTheta + lightTheta))), 2.0) * 0.5;
        v = mix(v, 1.0 - v, uInvert);
        pyvisualOutColor = vec4(vec3(v), 1.0);
    } else {
        pyvisualOutColor = vec4(vec3(mix(1.0, 0.0, uInvert)), 1.0);
    }
}

