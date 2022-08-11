///varying vec4 vertColor;

#version 120

varying vec2 uv;
uniform float xCenter = 0.0;
uniform float yCenter = 0.0;

const int MaxNumHoles = 2;
const int NumSpecsPerHole = 3;  // x, y, r

uniform float specs[MaxNumHoles * NumSpecsPerHole];
uniform float marginWidth;
uniform float left;
uniform float right;
uniform float  top;
uniform float bottom;
uniform int numHoles;
uniform float alphaGain;

float smootherstep(float edge1, float x)
{
	float edge0 = edge1 - 3;
    // Scale, and clamp x to 0..1 range
    x = clamp((x - edge0)/(edge1 - edge0), 0.0, 1.0);
    // Evaluate polynomial
    return x*x*x*(x*(x*6 - 15) + 10);
}


void main() {

	bool fragIsColored = false;

    float red = 0.0;
    float green = 0.0;
    float blue = 0.0;

	float alpha1 = 1.0;
	float alpha2 = 1.0;
	float alpha = 1.0;

    float dist1 = 0.0;
    float dist2 = 0.0;
    float dist = 0.0;

    float x = 0.0;
    float y = 0.0;
    float r1 = 0.0;
    float r2 = 0.0;

    vec2 m;

	x = specs[0];
    y = specs[1];
    r1 = specs[2];

    m = uv - vec2(x, y);
    dist1 = sqrt(m.x * m.x + m.y * m.y);
	alpha1 =  smootherstep(r1, dist1);

    x = specs[3];
    y = specs[4];
    r2 = specs[5];

    m = uv - vec2(x, y);
    dist2 = sqrt(m.x * m.x + m.y * m.y);
    alpha2 =  smootherstep(r2, dist2);

    if (alpha1 >= alpha2)
    	alpha = alpha2;
	else
		alpha = alpha1;

	// if (dist1 <= r1) { // inaper1
	// 	if (inpoly1) {
	// 		red = shape1_red;
	// 		green = shape1_green;
	// 		blue = shape1_blue;
	// 	} else if (inpoly2) {
	// 		red = back_red;
	// 		green = back_green;
	// 		blue = back_blue;
	// 	}
	// } else if (dist2 <= r2) { //inaper2
	// 	if (inpoly2) {
	// 		red = shape2_red;
	// 		green = shape2_green;
	// 		blue = shape2_blue;
	// 	} else if (inpoly1) {
	// 		red = back_red;
	// 		green = back_green;
	// 		blue = back_blue;
	// 	}
	// }

    gl_FragColor = vec4(red, green, blue, alpha * alphaGain);
	fragIsColored = true;

 	// define corners
    vec2 lowerLeft = vec2(left, bottom);
    vec2 upperLeft = vec2(left, top);
    vec2 lowerRight = vec2(right, bottom);
    vec2 upperRight = vec2(right, top);

     // rectangle edges
     if(uv.y < bottom) {
        if(uv.x < left) {
            dist = distance(uv, lowerLeft);
            alpha = smoothstep(marginWidth, 0, dist);
         } else if(uv.x > right) {
            dist = distance(uv, lowerRight);
            alpha = smoothstep(marginWidth, 0, dist);
         } else {
            alpha = smoothstep(bottom - marginWidth, bottom, uv.y);
         }
         gl_FragColor = vec4(red, green, blue, alpha * alphaGain);
      } else if(uv.y > top) {
        if(uv.x < left) {
            dist = distance(uv, upperLeft);
            alpha = smoothstep(marginWidth, 0, dist);
         } else if(uv.x > right) {
            dist = distance(uv, upperRight);
            alpha = smoothstep(marginWidth, 0, dist);
         } else {
            alpha = smoothstep(top + marginWidth, top, uv.y);
         }
         gl_FragColor = vec4(red, green, blue, alpha * alphaGain);
      } else if(uv.x < left) {
        if(uv.y > top) {
            dist = distance(uv, upperLeft);
            alpha = smoothstep(marginWidth, 0, dist);
         } else if(uv.y < bottom) {
            dist = distance(uv, lowerLeft);
            alpha = smoothstep(marginWidth, 0, dist);
         } else {
            alpha = smoothstep(left - marginWidth, left, uv.x);
         }
         gl_FragColor = vec4(red, green, blue, alpha * alphaGain);
      } else if(uv.x > right) {
       // alpha = smoothstep(right, right + marginWidth, uv.x);
       // gl_FragColor = vec4(red, green, blue, alpha);
        if(uv.y > top) {
            dist = distance(uv, upperRight);
            alpha = smoothstep(marginWidth, 0, dist);
         } else if(uv.y < bottom) {
            dist = distance(uv, lowerRight);
            alpha = smoothstep(marginWidth, 0, dist);
         } else {
            alpha = smoothstep(right + marginWidth, right, uv.x);
         }
         gl_FragColor = vec4(red, green, blue, alpha * alphaGain);
      }
}
