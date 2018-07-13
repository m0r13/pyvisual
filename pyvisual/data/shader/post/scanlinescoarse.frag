#version 150

uniform sampler2D uInputTexture;
uniform sampler2D uNoiseTexture;
uniform float time;

in vec2 TexCoord0;

out vec4 oFragColor;

float noise(vec2 p)
{
	float s = texture2D(uNoiseTexture, mod(vec2(1.,2.*cos(time))*time*8. + p*1., vec2(1.0, 1.0))).x;
	s *= s;
	return s;
}

#define PI 3.14159265359
highp float rand( const in vec2 uv ) {
    const highp float a = 12.9898, b = 78.233, c = 43758.5453;
    highp float dt = dot( uv.xy, vec2( a,b ) ), sn = mod( dt, PI );
    return fract(sin(sn) * c);
}

float onOff(float a, float b, float c)
{
	return step(c, sin(time + a*cos(time*b)));
}

float ramp(float y, float start, float end)
{
	float inside = step(start,y) - step(end,y);
	float fact = (y-start)/(end-start)*inside;
	return (1.-fact) * inside;
	
}

float stripes(vec2 uv)
{
	float noi = noise(uv*vec2(1.0,1.) + vec2(1.,3.));
    //float noi = rand(uv*vec2(0.5,1.) + vec2(1.,3.));
    // 0.5 instead of 0.45
	return ramp(mod(uv.y*4. + time/2. +sin(time + sin(time*0.63)),1.),0.45f,0.6)*noi;
}

vec3 getVideo(vec2 uv)
{
	vec2 look = uv;
	float window = 1./(1.+20.*(look.y-mod(time/4.,1.))*(look.y-mod(time/4.,1.)));
	//look.x = look.x + sin(look.y*10. + time)/50.*onOff(4.,4.,.3)*(1.+cos(time*80.))*window;
	float vShift = 0.4*onOff(2.,3.,.9)*(sin(time)*sin(time*20.) + 
										 (0.5 + 0.1*sin(time*200.)*cos(time)));
	look.y = mod(look.y + vShift * 0.25f, 1.);
	vec3 video = vec3(texture2D(uInputTexture, look));
	return video;
}

vec2 screenDistort(vec2 uv)
{
    return uv;
	uv -= vec2(.5,.5);
	uv = uv*1.2*(1./1.2+2.*uv.x*uv.x*uv.y*uv.y);
	uv += vec2(.5,.5);
	return uv;
}

void main() {
	//vec2 uv = fragCoord.xy / iResolution.xy;
    vec2 uv = TexCoord0;
	uv = screenDistort(uv);
	vec3 video = getVideo(uv);
	float vigAmt = 3.+.3*sin(time + 5.*cos(time*5.));
	float vignette = (1.-vigAmt*(uv.y-.5)*(uv.y-.5))*(1.-vigAmt*(uv.x-.5)*(uv.x-.5));
	
	video += stripes(uv);
	//video += vec3(noise(uv*2.)/2 - 0.1);
    //video += vec3(rand(uv + vec2(1.,2.*cos(time))*time*8.) / 4);
	//video *= vignette;
	//video *= (12.+mod(uv.y*30.+time,1.))/13.;
	
	oFragColor = vec4(video,1.0);
}

