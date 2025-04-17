package org.xper.utils;
import org.xper.drawing.RGBColor;

public class Lighting {
	RGBColor color = new RGBColor(1f,0f,0f);
	public String textureType = "SPECULAR";

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

	/**
	 * This combination of properties makes it so that the maximum contrast is 1.0x color
	 * and the minimum contrast is 0.4x the color.
	 * if the sum of spec, amb and diff goes over one, they're normalized. so 0.8 + 0.8 + 0.4 = 2.0
	 * And the minimum is the amb, so 0.8 / 2.0 = 0.4 in specular.
	 * In shade it is 0.4 (amb) / 1.0 (amb + diff) = 0.4
	 *
	 */
	void computeProperties() {
		if (textureType.equals("SPECULAR")) {
			spec = new float[]{0.8f,0.8f,0.8f,1f};
			shine = 0.7f*128f;

			amb = new float[]{(float)(color.getRed() * 0.8),(float)(color.getGreen() * 0.8), (float)(color.getBlue() * 0.8),1f};
			diff = new float[]{(float)(color.getRed() * 0.4),(float)(color.getGreen() * 0.4), (float)(color.getBlue() * 0.4),1f};
		} else if (textureType.equals("SHADE")){
			spec = new float[]{0f,0f,0f,1f};
			shine = 0f;
//			System.out.println("AC193801923: IM CALLED" );
			amb = new float[]{(float)(color.getRed() * 0.4),(float)(color.getGreen() * 0.4), (float)(color.getBlue() * 0.4),1f};
//			amb = new float[]{(float)(color.getRed() * 0.1),(float)(color.getGreen() * 0.1), (float)(color.getBlue() * 0.1),1f};
//			amb = new float[]{(float)(color.getRed() * 1),(float)(color.getGreen() * 1), (float)(color.getBlue() * 1),1f};
			diff = new float[]{(float)(color.getRed() * 1.0),(float)(color.getGreen() * 1.0), (float)(color.getBlue() * 1.0),1f};
//			diff = new float[]{(float)(color.getRed() * 0.6),(float)(color.getGreen() * 0.6), (float)(color.getBlue() * 0.6),1f};
//			diff = new float[]{(float)(color.getRed() * 0.9),(float)(color.getGreen() * 0.9), (float)(color.getBlue() * 0.9),1f};
//			diff = new float[]{(float)(color.getRed() * 0),(float)(color.getGreen() * 0), (float)(color.getBlue() * 0),1f};
		} else if (textureType.equals("2D")){
			spec = new float[]{0f,0f,0f,1f};
			amb = new float[]{(float)(color.getRed() * 1),(float)(color.getGreen() * 1), (float)(color.getBlue() * 1),1f};
			diff = new float[]{(float)(color.getRed() * 0),(float)(color.getGreen() * 0), (float)(color.getBlue() * 0),1f};
			shine = 0f;
		}
	}
// Version we used for AlexNet GA
//	void computeProperties() {
//		if (textureType.equals("SPECULAR")) {
//			spec = new float[]{1.0f, 1.0f, 1.0f, 1f};
////			spec = new float[]{0.8f,0.8f,0.8f,1f};
//			shine = 0.7f*128f;
//
////			amb = new float[]{(float)(color.getRed() * 0.9),(float)(color.getGreen() * 0.9), (float)(color.getBlue() * 0.9),1f}; // og
////			diff = new float[]{(float)(color.getRed() * 0.35),(float)(color.getGreen() * 0.35), (float)(color.getBlue() * 0.35),1f}; //og
//
//			double ambient = 1.0;
//			double diffusion = 1.0;
//			amb = new float[]{(float)(color.getRed() * ambient),(float)(color.getGreen() * ambient), (float)(color.getBlue() * ambient),1f};
//			diff = new float[]{(float)(color.getRed() * diffusion),(float)(color.getGreen() * diffusion), (float)(color.getBlue() * diffusion),1f};
//		} else if (textureType.equals("SHADE")){
//			spec = new float[]{0f,0f,0f,1f};
//			shine = 0f;
////			System.out.println("AC193801923: IM CALLED" );
//			double ambient = 0.4;
//			double diffusion = 1.0;
//			amb = new float[]{(float)(color.getRed() * ambient),(float)(color.getGreen() * ambient), (float)(color.getBlue() * ambient),1f};
////			amb = new float[]{(float)(color.getRed() * 1),(float)(color.getGreen() * 1), (float)(color.getBlue() * 1),1f};
////			diff = new float[]{(float)(color.getRed() * 0.6),(float)(color.getGreen() * 0.6), (float)(color.getBlue() * 0.6),1f}; //This was og
//			diff = new float[]{(float)(color.getRed() * diffusion),(float)(color.getGreen() * diffusion), (float)(color.getBlue() * diffusion),1f};
////			diff = new float[]{(float)(color.getRed() * 0),(float)(color.getGreen() * 0), (float)(color.getBlue() * 0),1f};
//		} else if (textureType.equals("2D")){
//			spec = new float[]{0f,0f,0f,1f};
//			amb = new float[]{(float)(color.getRed() * 1),(float)(color.getGreen() * 1), (float)(color.getBlue() * 1),100f};
//			diff = new float[]{(float)(color.getRed() * 0),(float)(color.getGreen() * 0), (float)(color.getBlue() * 0),1f};
//			shine = 0f;
//		}
//	}

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