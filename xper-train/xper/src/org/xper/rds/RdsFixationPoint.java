package org.xper.rds;

import java.util.concurrent.atomic.AtomicReference;

import org.lwjgl.opengl.GL11;
import org.xper.Dependency;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.Drawable;
import org.xper.drawing.RGBColor;
import org.xper.drawing.renderer.AbstractRenderer;

public class RdsFixationPoint implements Drawable {
	
	@Dependency
	RGBColor backgroundColor;
	@Dependency
	AtomicReference<RGBColor> fixationColor = new AtomicReference<RGBColor>();
	@Dependency
	float backgroundDepth = -10;
	@Dependency
	AtomicReference<Coordinates2D> fixationPosition = new AtomicReference<Coordinates2D>(new Coordinates2D(0,0)); // in degree
	
	@Dependency
	RdsSquare rdsBackground;
	@Dependency
	RdsSquare rdsFixation;

	@Override
	public void draw(Context context) {
		GL11.glColor3f(backgroundColor.getRed(), backgroundColor.getGreen(), backgroundColor.getBlue());
		GL11.glPushMatrix();
		GL11.glTranslated (0, 0, backgroundDepth);
		rdsBackground.draw(context);
		GL11.glPopMatrix();
		
		RGBColor c = fixationColor.get();
		GL11.glColor3f(c.getRed(), c.getGreen(), c.getBlue());
		GL11.glPushMatrix();
		Coordinates2D p = fixationPosition.get();
		AbstractRenderer r = context.getRenderer();
		GL11.glTranslated(r.deg2mm(p.getX()), r.deg2mm(p.getY()), 0); 
		rdsFixation.draw(context);
		GL11.glPopMatrix();
	}

	public RGBColor getBackgroundColor() {
		return backgroundColor;
	}

	public void setBackgroundColor(RGBColor backgroundColor) {
		this.backgroundColor = backgroundColor;
	}

	public RGBColor getFixationColor() {
		return fixationColor.get();
	}

	public void setFixationColor(RGBColor fixationColor) {
		this.fixationColor.set(fixationColor);
	}

	public float getBackgroundDepth() {
		return backgroundDepth;
	}

	public void setBackgroundDepth(float backgroundDepth) {
		this.backgroundDepth = backgroundDepth;
	}

	public RdsSquare getRdsBackground() {
		return rdsBackground;
	}

	public void setRdsBackground(RdsSquare rdsBackground) {
		this.rdsBackground = rdsBackground;
	}

	public RdsSquare getRdsFixation() {
		return rdsFixation;
	}

	public void setRdsFixation(RdsSquare rdsFixation) {
		this.rdsFixation = rdsFixation;
	}

	public Coordinates2D getFixationPosition() {
		return fixationPosition.get();
	}

	public void setFixationPosition(Coordinates2D fixationPosition) {
		this.fixationPosition.set(fixationPosition);
	}

	public void setFixationSize(float value) {
		rdsFixation.setSize(value);
		rdsFixation.init();
	}

}
