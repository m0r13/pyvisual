// uInputTexture is (still) built-in to Shader class
uniform sampler2D uInputTexture; // {"skip" : true, "alias" : "input"}

in vec2 TexCoord0;
out vec4 oFragColor;

layout(std430, binding=0) buffer uBuffer {
    float data[];
};
uniform int uCount; // {"skip" : true}

uniform float uHeight; // {"default" : 0.01}
uniform float uSoftness; // {"default" : 0.1}

uniform float uCenter; // {"default" : 0, "range" : [0, 1]}

void main() {
    vec2 uv = TexCoord0;
    int i = int(floor(uv.x * uCount));
    float y0 = data[i];
    float y1 = data[i+1];
    if (i == uCount - 1) {
        y1 = y0;
    }
    float x0 = float(i) / float(uCount - 1);
    float x1 = min(1.0, float(i+1) / float(uCount - 1));
    float x = uv.x;

    float alpha = uv.x * uCount - float(i);
    float y = mix(y0, y1, alpha);
    float pos = 1.0 - uv.y - mix(0.0, 0.5, uCenter);
    float d = pos - y;
    // using the actual point-line distance doesn't work so well
    //float d = abs((y1 - y0) * x - (x1 - x0) * pos + x1*y0 - y1*x0) / sqrt((y1-y0)*(y1-y0) + (x1-x0)*(x1-x0));

    float r = uHeight * 0.5;
    float s = uHeight * uSoftness * 0.5;
    float v = smoothstep(-(r + s), -r, d) * (1.0 - smoothstep(r, r + s, d));

    oFragColor = vec4(vec3(v), 1.0);
}

