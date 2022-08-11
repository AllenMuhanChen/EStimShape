package org.xper.sach.drawing.screenobj;

import org.lwjgl.opengl.GL11;
import org.xper.drawing.Context;
import org.xper.drawing.object.Rectangle;
//import org.xper.drawing.Coordinates2D;
//import org.xper.drawing.RGBColor;

public class RectangleObject extends Rectangle {

	public static double width = 3;	// if this is changed, you need to flush all to-do stimuli
	public static double height = 3;
	public double tx = 0;
	public double ty = 80;		// if this is changed, you need to flush all to-do stimuli
	public double tz = 0;
	public float r = 0.0f;
	public float g = 1.0f;
	public float b = 1.0f;
	boolean solid = true;

	public RectangleObject() {
		super(width, height);
		// TODO Auto-generated constructor stub
	}
	
	public RectangleObject(float r, float g, float b) {
		super(width, height);
		this.r = r;
		this.g = g;
		this.b = b;
	}
	
	public RectangleObject(float r, float g, float b, double w, double h) {
		super(w, h);
		width = w;
		height = h;
		this.r = r;
		this.g = g;
		this.b = b;
	}
	
	public RectangleObject(float r, float g, float b, double w, double h, double tx, double ty, double tz) {
		super(w, h);
		width = w;
		height = h;
		this.r = r;
		this.g = g;
		this.b = b;
		this.tx = tx;
		this.ty = ty;
		this.tz = tz;
	}
	
	public void drawRectangle(Context context) {
		GL11.glPushAttrib(GL11.GL_COLOR_BUFFER_BIT);
		GL11.glColor3f(r, g, b);
		GL11.glPushMatrix();
		GL11.glTranslated(tx, ty, tz);
		this.setSolid(solid);
		this.draw(null);
		GL11.glPopMatrix();
		GL11.glPopAttrib();
	}
	
	public double getWidth() {
		return width;
	}

	public double getHeight() {
		return height;
	}

	public double getTx() {
		return tx;
	}

	public double getTy() {
		return ty;
	}

	public double getTz() {
		return tz;
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
