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
		GL11.glViewport (0, 0, getVpWidth(), getVpHeight());

		GL11.glMatrixMode (GL11.GL_PROJECTION);
		GL11.glLoadIdentity();

		double bottom = getYmin() * PROJECTION_NEAR / getDistance();
		double top = (getYmax() + getVunit()) * PROJECTION_NEAR / getDistance();
		if (isInverted()) {
			double left = getXmax() * PROJECTION_NEAR / getDistance();
			double right = (getXmin() - getHunit()) * PROJECTION_NEAR / getDistance();
			GL11.glFrustum (left, right, bottom, top, PROJECTION_NEAR, getDistance() + getDepth());
//			System.out.println("leftport: " + left + ", " + right + ", " + bottom + ", " + top + ", " + PROJECTION_NEAR + ", " + distance + ", " + depth);
		} else {
			double left = getXmin() * PROJECTION_NEAR / getDistance();
			double right = (getXmax() + getHunit()) * PROJECTION_NEAR / getDistance();
			GL11.glFrustum (left, right, bottom, top, PROJECTION_NEAR, getDistance() + getDepth());
		}

		GL11.glMatrixMode (GL11.GL_MODELVIEW);
		GL11.glLoadIdentity();
		if (doStereo)
			GLU.gluLookAt ((float)le_pos, 0, (float) getDistance(), 0, 0, 0, 0, 1, 0);
		else
			GLU.gluLookAt (0, 0, (float) getDistance(), 0, 0, 0, 0, 1, 0);

	}

	@Override
	public void setupRight() {
		GL11.glViewport(getVpWidth(), 0, getVpWidth(), getVpHeight());

		GL11.glMatrixMode (GL11.GL_PROJECTION);
		GL11.glLoadIdentity();

		double bottom = getYmin() * PROJECTION_NEAR / getDistance();
		double top = (getYmax() + getVunit()) * PROJECTION_NEAR / getDistance();
		if (isInverted()) {
			double left = getXmax() * PROJECTION_NEAR / getDistance();
			double right = (getXmin() - getHunit()) * PROJECTION_NEAR / getDistance();
			GL11.glFrustum (left, right, bottom, top, PROJECTION_NEAR, getDistance() + getDepth());
//			System.out.println("rightport: " + left + ", " + right + ", " + bottom + ", " + top + ", " + PROJECTION_NEAR + ", " + distance + ", " + depth);
		} else {
			double left = getXmin() * PROJECTION_NEAR / getDistance();
			double right = (getXmax() + getHunit()) * PROJECTION_NEAR / getDistance();
			GL11.glFrustum (left, right, bottom, top, PROJECTION_NEAR, getDistance() + getDepth());
		}

		GL11.glMatrixMode (GL11.GL_MODELVIEW);
		GL11.glLoadIdentity();
		if (doStereo)
			GLU.gluLookAt ((float)re_pos, 0, (float) getDistance(), 0, 0, 0, 0, 1, 0);
		else
			GLU.gluLookAt (0, 0, (float) getDistance(), 0, 0, 0, 0, 1, 0);
	}
	
	public void setDoStereo(boolean doStereo) {
		this.doStereo = doStereo;
	}
}
