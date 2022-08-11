package org.xper.sach.renderer;

import org.lwjgl.opengl.GL11;
import org.lwjgl.util.glu.GLU;
import org.xper.drawing.renderer.StereoRenderer;
import org.xper.drawing.RGBColor;

public class SachPerspectiveStereoRenderer extends StereoRenderer {
	
	public RGBColor backgroundColor = new RGBColor(0f,0f,0f);	// initialize to black background color
	float r,g,b;
	boolean doStereo = false;
	
	public void init() {
		super.init();
		r = backgroundColor.getRed();
		g = backgroundColor.getGreen();
		b = backgroundColor.getBlue();
		GL11.glClearColor(r, g, b, 0f);
	}
	
	public RGBColor getRgbColor() {
		return backgroundColor;
	}
	public void setRgbColor(RGBColor rgbColor) {
		this.backgroundColor = rgbColor;
	}
	
	@Override
	public void setupLeft() {
		GL11.glViewport (0, 0, vpWidth, vpHeight);

		GL11.glMatrixMode (GL11.GL_PROJECTION);
		GL11.glLoadIdentity();

		double bottom = ymin * PROJECTION_NEAR / distance;
		double top = (ymax + vunit) * PROJECTION_NEAR / distance;
		if (inverted) {
			double left = xmax * PROJECTION_NEAR / distance;
			double right = (xmin - hunit) * PROJECTION_NEAR / distance;
			GL11.glFrustum (left, right, bottom, top, PROJECTION_NEAR, distance + depth);
//			System.out.println("leftport: " + left + ", " + right + ", " + bottom + ", " + top + ", " + PROJECTION_NEAR + ", " + distance + ", " + depth);
		} else {
			double left = xmin * PROJECTION_NEAR / distance;
			double right = (xmax + hunit) * PROJECTION_NEAR / distance;
			GL11.glFrustum (left, right, bottom, top, PROJECTION_NEAR, distance + depth);
		}

		GL11.glMatrixMode (GL11.GL_MODELVIEW);
		GL11.glLoadIdentity();
		if (doStereo)
			GLU.gluLookAt ((float)le_pos, 0, (float)distance, 0, 0, 0, 0, 1, 0);
		else
			GLU.gluLookAt (0, 0, (float)distance, 0, 0, 0, 0, 1, 0);

	}

	@Override
	public void setupRight() {
		GL11.glViewport(vpWidth, 0, vpWidth, vpHeight);

		GL11.glMatrixMode (GL11.GL_PROJECTION);
		GL11.glLoadIdentity();

		double bottom = ymin * PROJECTION_NEAR / distance;
		double top = (ymax + vunit) * PROJECTION_NEAR / distance;
		if (inverted) {
			double left = xmax * PROJECTION_NEAR / distance;
			double right = (xmin - hunit) * PROJECTION_NEAR / distance;
			GL11.glFrustum (left, right, bottom, top, PROJECTION_NEAR, distance + depth);
//			System.out.println("rightport: " + left + ", " + right + ", " + bottom + ", " + top + ", " + PROJECTION_NEAR + ", " + distance + ", " + depth);
		} else {
			double left = xmin * PROJECTION_NEAR / distance;
			double right = (xmax + hunit) * PROJECTION_NEAR / distance;
			GL11.glFrustum (left, right, bottom, top, PROJECTION_NEAR, distance + depth);
		}

		GL11.glMatrixMode (GL11.GL_MODELVIEW);
		GL11.glLoadIdentity();
		if (doStereo)
			GLU.gluLookAt ((float)re_pos, 0, (float)distance, 0, 0, 0, 0, 1, 0);
		else
			GLU.gluLookAt (0, 0, (float)distance, 0, 0, 0, 0, 1, 0);
	}
	
	public void setDoStereo(boolean doStereo) {
		this.doStereo = doStereo;
	}
}
