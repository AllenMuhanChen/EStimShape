package org.xper.drawing.object;

import org.lwjgl.opengl.GL11;
import org.xper.Dependency;
import org.xper.drawing.Context;
import org.xper.drawing.RGBColor;
import org.xper.drawing.ScreenMarker;
import org.xper.drawing.renderer.AbstractRenderer;

public class AlternatingScreenMarker implements ScreenMarker {
	@Dependency
	protected int viewportIndex = 0;
	@Dependency
	protected int size = 20;

	protected int i = 0;
	protected RGBColor whiteColor = new RGBColor(1, 1, 1);
	protected RGBColor blackColor = new RGBColor(0, 0, 0);

	public void next() {
		i++;
	}

	protected void drawMarker(Context context, RGBColor firstColor, RGBColor secondColor) {
		AbstractRenderer renderer = context.getRenderer();

		double lx = renderer.getXmin() + size/2;
		double ly = renderer.getYmin() + size/2;
		double rx = renderer.getXmax() - size/2;
		double ry = renderer.getYmin() + size/2;
		RGBColor l = null;
		RGBColor r = null;
		if (i % 2 == 0) {
			l = firstColor;
			r = secondColor;
		} else {
			l = secondColor;
			r = firstColor;
		}
		double z = 0;
		
		GL11.glColor4f(l.getRed(), l.getGreen(), l.getBlue(), 1f);
		
		GL11.glPushMatrix();
			GL11.glTranslated(lx, ly, z);
			GL11.glBegin(GL11.GL_QUADS);
				GL11.glVertex3d(-size/2., -size/2., z);
				GL11.glVertex3d(size/2., -size/2., z);
				GL11.glVertex3d(size/2., size/2., z);
				GL11.glVertex3d(-size/2., size/2., z);
			GL11.glEnd();
		GL11.glPopMatrix();
		

		GL11.glColor4f(r.getRed(), r.getGreen(), r.getBlue(), 1f);
		GL11.glPushMatrix();
			GL11.glTranslated(rx, ry, z);
			GL11.glBegin(GL11.GL_QUADS);
				GL11.glVertex3d(-size/2., -size/2., z);
				GL11.glVertex3d(size/2., -size/2., z);
				GL11.glVertex3d(size/2., size/2., z);
				GL11.glVertex3d(-size/2., size/2., z);
			GL11.glEnd();
		GL11.glPopMatrix();
	}

	
	public void draw(Context context) {
		if (context.getViewportIndex() == viewportIndex) {
			drawMarker(context, whiteColor, blackColor);
		}
	}
	
	public void drawAllOff(Context context) {
		if (context.getViewportIndex() == viewportIndex) {
			drawMarker(context, blackColor, blackColor);
		}
	}

	public int getViewportIndex() {
		return viewportIndex;
	}

	public void setViewportIndex(int viewportIndex) {
		this.viewportIndex = viewportIndex;
	}

	public int getSize() {
		return size;
	}

	public void setSize(int size) {
		this.size = size;
	}
}
