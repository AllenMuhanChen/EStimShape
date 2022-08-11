package org.xper.sach.drawing.screenobj;

import org.lwjgl.opengl.GL11;
import org.xper.drawing.Context;
import org.xper.drawing.object.Circle;

public class CircleObject extends Circle {

	double radius = 10;		// units: mm? 	// if this is changed, you need to flush all to-do stimuli
	double tx = 0;
	double ty = 0;			// if this is changed, you need to flush all to-do stimuli
	double tz = 0;
	float r = 0.5f;
	float g = 0.5f;
	float b = 0.5f;
	boolean solid = false;

	public CircleObject() {
		//super();
		super.setRadius(radius);
	}
	
	public CircleObject(float r, float g, float b) {
		super.setRadius(radius);
		this.r = r;
		this.g = g;
		this.b = b;
	}
	
	public CircleObject(double radius, double tx, double ty, double tz, float r, float g, float b) {
		this.radius = radius;
		super.setRadius(radius);
		this.tx = tx;
		this.ty = ty;
		this.tz = tz;
		this.r = r;
		this.g = g;
		this.b = b;
	}
	
	public void draw(Context context) {
		GL11.glPushAttrib(GL11.GL_COLOR_BUFFER_BIT);
		GL11.glColor3f(r, g, b);
		GL11.glPushMatrix();
		GL11.glTranslated(tx, ty, tz);
		super.setSolid(solid);
		if (!solid) { GL11.glLineWidth(1f); }
		super.draw(null);
		GL11.glPopMatrix();
		GL11.glPopAttrib();
	}
	
	public double getRadius() {
		return radius;
	}
	
	public void setRadius(double radius) {
		this.radius = radius;
	}

	public double getTx() {
		return tx;
	}

	public void setTx(double tx) {
		this.tx = tx;
	}

	public double getTy() {
		return ty;
	}

	public void setTy(double ty) {
		this.ty = ty;
	}

	public double getTz() {
		return tz;
	}

	public void setTz(double tz) {
		this.tz = tz;
	}

	public float getR() {
		return r;
	}

	public void setR(float r) {
		this.r = r;
	}

	public float getG() {
		return g;
	}

	public void setG(float g) {
		this.g = g;
	}

	public float getB() {
		return b;
	}

	public void setB(float b) {
		this.b = b;
	}

}
