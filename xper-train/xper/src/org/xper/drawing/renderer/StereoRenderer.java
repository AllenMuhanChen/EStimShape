package org.xper.drawing.renderer;

import org.lwjgl.opengl.GL11;
import org.xper.Dependency;
import org.xper.drawing.Context;
import org.xper.drawing.Drawable;

public abstract class StereoRenderer extends AbstractRenderer {

	@Dependency
	boolean inverted = true;
	
	double le_pos;
	double re_pos;

	protected void calculateCoordinates() {
		super.calculateCoordinates();

		xmin = -width / 4.0 + hunit / 2.0;
		xmax = width / 4.0 - hunit / 2.0;

		vpWidth = widthInPixel / 2;
		vpWidthmm = width / 2.0;

		le_pos = -pupilDistance / 2.0;
		re_pos = pupilDistance / 2.0;

	}

	public void init() {
		calculateCoordinates();
	}
	
	public void draw(Drawable scene, Context context) {
		GL11.glPushMatrix ();
		setupLeft ();
		drawLeft (scene, context);
		GL11.glPopMatrix ();

		GL11.glPushMatrix ();
		setupRight ();
		drawRight (scene, context);	
		GL11.glPopMatrix ();
	}
	
	protected abstract void setupLeft();
	protected abstract void setupRight();

	protected void drawLeft(Drawable scene, Context context) {
		context.setViewportIndex(0);
		context.setRenderer(this);
		scene.draw(context);
	}

	protected void drawRight(Drawable scene, Context context) {
		context.setViewportIndex(1);
		context.setRenderer(this);
		scene.draw(context);
	}

	public boolean isInverted() {
		return inverted;
	}

	public void setInverted(boolean inverted) {
		this.inverted = inverted;
	}
}
