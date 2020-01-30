package org.xper.drawing.renderer;

import org.lwjgl.opengl.GL11;
import org.xper.Dependency;

public class OrthoRenderer extends AbstractRenderer {
	
	@Dependency
	double orthoDepth = 6000;
	
	protected void calculateCoordinates() {
		super.calculateCoordinates();
		zmin = -orthoDepth;
		zmax = orthoDepth;
	}
	
	public void init() {
		super.init();
		GL11.glMatrixMode(GL11.GL_PROJECTION);
		GL11.glLoadIdentity();
		GL11.glOrtho(xmin, xmax+hunit, ymin, ymax+vunit, -zmax, -zmin);
		GL11.glMatrixMode(GL11.GL_MODELVIEW);
		GL11.glLoadIdentity();
	}

	public double getOrthoDepth() {
		return orthoDepth;
	}

	public void setOrthoDepth(double orthoDepth) {
		this.orthoDepth = orthoDepth;
	}
}
