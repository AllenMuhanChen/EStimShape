package org.xper.sach.drawing.screenobj;

import org.lwjgl.opengl.GL11;
import org.xper.drawing.Context;
import org.xper.drawing.object.Circle;

public class TransparentCircleObject extends Circle {

	double radius = 10;		// units: mm? 	// if this is changed, you need to flush all to-do stimuli
	double tx = 0;
	double ty = 0;			// if this is changed, you need to flush all to-do stimuli
	double tz = 0;
	float r = 0.5f;
	float g = 0.5f;
	float b = 0.5f;
	float a = 0.7f;
	boolean solid = true;

	public TransparentCircleObject() {
		//super();
		super.setRadius(radius);
	}
	
	public TransparentCircleObject(float r, float g, float b, float a) {
		super.setRadius(radius);
		this.r = r;
		this.g = g;
		this.b = b;
		this.a = a;
	}
	
	public TransparentCircleObject(double radius, double tx, double ty, double tz, float r, float g, float b, float a) {
		this.radius = radius;
		super.setRadius(radius);
		this.tx = tx;
		this.ty = ty;
		this.tz = tz;
		this.r = r;
		this.g = g;
		this.b = b;
		this.a = a;
	}
	
	public void draw(Context context) {
		GL11.glPushAttrib(GL11.GL_COLOR_BUFFER_BIT);
		GL11.glPushMatrix();
		
		GL11.glColor4f(r, g, b, a);
		GL11.glEnable(GL11.GL_BLEND);
		GL11.glBlendFunc(GL11.GL_ZERO, GL11.GL_SRC_ALPHA);
		
		GL11.glTranslated(tx, ty, tz);
		super.setSolid(solid);
		super.draw(context);
		GL11.glDisable(GL11.GL_BLEND);
		
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
	
	public float getA() {
		return a;
	}

	public void setA(float a) {
		this.a = a;
	}

}
