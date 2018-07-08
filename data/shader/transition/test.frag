uniform sampler2D uInputTexture,uTexture1, uTexture2;
uniform float uAlpha;
//uniform vec2 resolution;
uniform float strength;

in vec2 TexCoord0;
out vec4 oFragColor;

const float PI=3.141592653589793;
float Linear_ease(in float begin,in float change,in float duration,in float time){return change*time/duration+begin;
}float Exponential_easeInOut(in float begin,in float change,in float duration,in float time){if(time==0.0) return begin;
else if(time==duration) return begin+change;
time=time/(duration/2.0);
if(time<1.0) return change/2.0*pow(2.0,10.0*(time-1.0))+begin;
return change/2.0*(-pow(2.0,-10.0*(time-1.0))+2.0)+begin;
}float Sinusoidal_easeInOut(in float begin,in float change,in float duration,in float time){return -change/2.0*(cos(PI*time/duration)-1.0)+begin;
}float random(in vec3 scale,in float seed){return fract(sin(dot(gl_FragCoord.xyz+seed,scale))*43758.5453+seed);
}vec3 crossFade(in vec2 uv,in float dissolve){return mix(texture2D(uTexture1,uv).rgb,texture2D(uTexture2,uv).rgb,dissolve);
}void main(){vec2 texCoord=TexCoord0;
vec2 center=vec2(Linear_ease(0.25,0.5,1.0,uAlpha),0.5);
float dissolve=Exponential_easeInOut(0.0,1.0,1.0,uAlpha);
float strength=Sinusoidal_easeInOut(0.0,strength,0.5,uAlpha);
vec3 color=vec3(0.0);
float total=0.0;
vec2 toCenter=center-texCoord;
float offset=random(vec3(12.9898,78.233,151.7182),0.0);
for(float t=0.0;
t<=40.0;
t++){float percent=(t+offset)/40.0;
float weight=4.0*(percent-percent*percent);
color+=crossFade(texCoord+toCenter*percent*strength,dissolve)*weight;
total+=weight;
}oFragColor=vec4(color/total,1.0);
}
