// adapted from: http://callumhay.blogspot.com/2010/09/gaussian-blur-shader-glsl.html

uniform sampler2D uInputTexture;  // Texture that will be blurred by this shader

uniform float uSigma;     // The uSigma value for the gaussian function: higher value means more blur
                         // A good value for 9x9 is around 3 to 5
                         // A good value for 7x7 is around 2.5 to 4
                         // A good value for 5x5 is around 2 to 3.5
                         // ... play around with this based on what you need :)

uniform vec2 uDirection;

// TODO offer different variants
const float numBlurPixelsPerSide = 9.0f;

in vec2 TexCoord0;
out vec4 oFragColor;

const float pi = 3.14159265f;

void main() {
    // Incremental Gaussian Coefficent Calculation (See GPU Gems 3 pp. 877 - 889)
    vec3 incrementalGaussian;
    incrementalGaussian.x = 1.0f / (sqrt(2.0f * pi) * uSigma);
    incrementalGaussian.y = exp(-0.5f / (uSigma * uSigma));
    incrementalGaussian.z = incrementalGaussian.y * incrementalGaussian.y;

    vec4 avgValue = vec4(0.0f, 0.0f, 0.0f, 0.0f);
    float coefficientSum = 0.0f;

    // Take the central sample first...
    avgValue += texture2D(uInputTexture, TexCoord0) * incrementalGaussian.x;
    coefficientSum += incrementalGaussian.x;
    incrementalGaussian.xy *= incrementalGaussian.yz;

    vec2 blurOffset = uDirection / vec2(textureSize(uInputTexture, 0).xy);

    // Go through the remaining 8 vertical samples (4 on each side of the center)
    for (float i = 1.0f; i <= numBlurPixelsPerSide; i++) { 
        avgValue += texture2D(uInputTexture, TexCoord0 - i * blurOffset) * incrementalGaussian.x;
        avgValue += texture2D(uInputTexture, TexCoord0 + i * blurOffset) * incrementalGaussian.x;
        coefficientSum += 2 * incrementalGaussian.x;
        incrementalGaussian.xy *= incrementalGaussian.yz;
    }

    oFragColor = avgValue / coefficientSum;
}
