package org.xper.drawing.object;

import org.lwjgl.opengl.GL11;
import org.xper.Dependency;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.Drawable;
import org.xper.drawing.RGBColor;
import org.xper.drawing.renderer.AbstractRenderer;

public class FixationPoint implements Drawable {

	@Dependency
	Coordinates2D fixationPosition;
	@Dependency
	double size; // in mm
	@Dependency
	RGBColor color;
	@Dependency
	boolean solid = true;
	

	/**
	 * @param context ignored.
	 */
	public void draw(Context context) {
		AbstractRenderer renderer = context.getRenderer();
		double x = renderer.deg2mm(fixationPosition.getX());
		double y = renderer.deg2mm(fixationPosition.getY());
		Coordinates2D posInMm = new Coordinates2D(x,y);
		
		drawVertexes(posInMm);
	}

	void drawVertexes(Coordinates2D posInMm) {
		double z = 0;
		
		GL11.glColor4f(color.getRed(), color.getGreen(), color.getBlue(), 1f);
		
		GL11.glPushMatrix();
		GL11.glTranslated(posInMm.getX(), posInMm.getY(), z);
		if (solid) {
			GL11.glBegin(GL11.GL_QUADS);
		} else {
			GL11.glBegin(GL11.GL_LINE_LOOP);
		}
			GL11.glVertex3d(-size/2., -size/2., z);
			GL11.glVertex3d(size/2., -size/2., z);
			GL11.glVertex3d(size/2., size/2., z);
			GL11.glVertex3d(-size/2., size/2., z);
		GL11.glEnd();
		GL11.glPopMatrix();
	}

	public Coordinates2D getFixationPosition() {
		return fixationPosition;
	}

	public void setFixationPosition(Coordinates2D fixationPosition) {
		this.fixationPosition = fixationPosition;
	}

	public RGBColor getColor() {
		return color;
	}

	public void setColor(RGBColor color) {
		this.color = color;
	}

	public double getSize() {
		return size;
	}

	public void setSize(double size) {
		this.size = size;
	}

	public boolean isSolid() {
		return solid;
	}

	public void setSolid(boolean solid) {
		this.solid = solid;
	}
}
