// uInputTexture is (still) built-in to Shader class
uniform sampler2D uInputTexture; // {"skip" : true, "alias" : "input"}

in vec2 TexCoord0;
out vec4 oFragColor;

layout(std430, binding=0) buffer uBuffer {
    float data[];
};
uniform int uCount; // {"skip" : true}

uniform float uScale; // {"default" : 1.0}
uniform float uOffset; // {"default" : 0.0}

uniform float uSpacing; // {"default" : 0.0, "range" : [0.0, 1.0]}

void main() {
    vec2 uv = TexCoord0;
    if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
        discard;
    }

    int i = int(floor(uv.x * uCount));
    float alpha = uv.x * uCount - float(i);

    if (alpha < uSpacing*0.5 || alpha > (1.0 - uSpacing*0.5)) {
        discard;
    }

    float value = (data[i] * uScale) + uOffset;
    if ((1.0 - uv.y) < value) {
        oFragColor = vec4(vec3(1.0), 1.0);
    } else {
        discard;
    }
}

