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
uniform float uCenter; // {"default" : 0, "range" : [0, 1]}

uniform float uThickness; // {"default" : 0.2}
uniform float uSoftness; // {"default" : 1.0}

// https://iquilezles.org/www/articles/distfunctions2d/distfunctions2d.htm
float sdLine( in vec2 p, in vec2 a, in vec2 b )
{
	vec2 pa = p-a, ba = b-a;
	float h = clamp( dot(pa,ba)/dot(ba,ba), 0.0, 1.0 );
	return length( pa - ba*h );
}

vec3 line( in vec3 buf, in vec2 a, in vec2 b, in vec2 p, in vec2 w, in vec4 col )
{
   float f = sdLine( p, a, b );
   float g = fwidth(f)*w.y;
   return mix( buf, col.xyz, col.w*(1.0-smoothstep(w.x-g, w.x+g, f)) );
}

void main() {
    const int radius = 1;

    vec2 uv = TexCoord0;
    vec2 size = textureSize(uInputTexture, 0);
    float aspectAdjust = size.x / size.y;

    int initialI = int(floor(uv.x * uCount));
    float value = 0.0;

    for (int i = initialI-radius; i <= initialI+radius; i++) {
        float y0 = data[i] * uScale + uOffset;
        float y1 = data[i+1] * uScale + uOffset;
        if (i == uCount - 1) {
            y1 = y0;
        }
        float x0 = float(i) / float(uCount - 1) * aspectAdjust;
        float x1 = min(1.0, float(i+1) / float(uCount - 1)) * aspectAdjust;
        float x = uv.x * aspectAdjust;

        float alpha = uv.x * uCount - float(i);
        float y = mix(y0, y1, alpha);
        float pos = 1.0 - uv.y - mix(0.0, 0.5, uCenter);

        // very naive vertical distance point-line
        //float d = pos - y;

        // distance point-line, lines are not connected at all
        /*
        float d = abs((y1 - y0) * x - (x1 - x0) * pos + x1*y0 - y1*x0) / sqrt((y1-y0)*(y1-y0) + (x1-x0)*(x1-x0));

        float r = uHeight * 0.5;
        float s = uHeight * uSoftness * 0.5;
        float v = smoothstep(-(r + s), -r, d) * (1.0 - smoothstep(r, r + s, d));
        value += v;
        */

        // proper 2d-sdf line
        vec2 p = uv;
        p.x *= aspectAdjust;
        p.y = pos;
        float d = line(vec3(0.0), vec2(x0, y0), vec2(x1, y1), p, vec2(0.01 * uThickness, uSoftness), vec4(1.0)).r;
        value += d;
    }

    oFragColor = vec4(vec3(value), 1.0);
}

