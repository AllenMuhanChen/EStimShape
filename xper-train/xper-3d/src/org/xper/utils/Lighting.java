package org.xper.utils;
import org.xper.drawing.RGBColor;

public class Lighting {
	RGBColor color = new RGBColor(1f,0f,0f);
	String textureType = "SPECULAR";

	float shine;
	float [] amb;
	float [] diff;
	float [] spec;

	public void setLightColor(RGBColor color) {
		this.color = color;
		computeProperties();
	}

	public void setTextureType(String textureType) {
		this.textureType = textureType;
		computeProperties();
	}

	void computeProperties() {
		if (textureType.equals("SPECULAR")) {
			spec = new float[]{0.8f,0.8f,0.8f,1f};
			shine = 0.7f*128f;

			amb = new float[]{(float)(color.getRed() * 0.9),(float)(color.getGreen() * 0.9), (float)(color.getBlue() * 0.9),1f};
			diff = new float[]{(float)(color.getRed() * 0.35),(float)(color.getGreen() * 0.35), (float)(color.getBlue() * 0.35),1f};
		} else if (textureType.equals("SHADE")){
			spec = new float[]{0f,0f,0f,1f};
			shine = 0f;
//			System.out.println("AC193801923: IM CALLED" );
			amb = new float[]{(float)(color.getRed() * 0.4),(float)(color.getGreen() * 0.4), (float)(color.getBlue() * 0.4),1f};
//			amb = new float[]{(float)(color.getRed() * 1),(float)(color.getGreen() * 1), (float)(color.getBlue() * 1),1f};
			diff = new float[]{(float)(color.getRed() * 0.6),(float)(color.getGreen() * 0.6), (float)(color.getBlue() * 0.6),1f};
//			diff = new float[]{(float)(color.getRed() * 0),(float)(color.getGreen() * 0), (float)(color.getBlue() * 0),1f};
		} else if (textureType.equals("2D")){
			spec = new float[]{0f,0f,0f,1f};
			amb = new float[]{(float)(color.getRed() * 1),(float)(color.getGreen() * 1), (float)(color.getBlue() * 1),100f};
			diff = new float[]{(float)(color.getRed() * 0),(float)(color.getGreen() * 0), (float)(color.getBlue() * 0),1f};
			shine = 0f;
		}
	}

	public float[] getAmbient() {
		return amb;
	}
	public float[] getDiffuse() {
		return diff;
	}
	public float[] getSpecular() {
		return spec;
	}
	public float getShine() {
		return shine;
	}
}