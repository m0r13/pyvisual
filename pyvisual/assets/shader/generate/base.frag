// uInputTexture is (still) built-in to Shader class
uniform sampler2D uInputTexture; // {"skip" : true, "alias" : "input"}

uniform float uTime; // {"alias" : "time"}

// alias these inputs as they are "built-in" into the filter nodes
// and should appear different from the other uniform inputs
uniform sampler2D uTimeMaskTexture; // {"alias" : "time_mask"}
uniform float uMaskTimeD0; // {"alias" : "time_d0", "default" : 0.0}
uniform float uMaskTimeD1; // {"alias" : "time_d1", "default" : 0.0}

in vec2 TexCoord0;
out vec4 oFragColor;

vec4 generateFrag(vec2, float);

void main( ) {
    vec2 uv = TexCoord0;
    float mask = texture2D(uTimeMaskTexture, uv).r;
    float time = uTime + mix(uMaskTimeD0, uMaskTimeD1, mask);
    oFragColor = generateFrag(uv, time);
}

