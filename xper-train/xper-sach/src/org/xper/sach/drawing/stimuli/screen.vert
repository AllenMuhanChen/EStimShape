
#version 110

varying vec2 uv;

void main() {
	gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
	//gl_Position = gl_Vertex;
	//uv = vec2(gl_MultiTexCoord0);
	uv = vec2(gl_Vertex);
}
