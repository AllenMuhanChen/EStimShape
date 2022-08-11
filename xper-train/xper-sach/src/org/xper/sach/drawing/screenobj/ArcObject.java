package org.xper.sach.drawing.screenobj;

import org.lwjgl.opengl.GL11;
import org.lwjgl.util.glu.PartialDisk;
import org.xper.drawing.Context;
import org.xper.drawing.Drawable;

public class ArcObject implements Drawable {
	
	public static float radius = 90;			// when changing any static variable, you need to purge and recreate stimuli (so their targetPositions are correctly calculated)
	public static float width = 5;				
	public static float startAngle = -80;		// deg
	public static float angularLength = 160;	// deg
	int slicesPerDegree = 5;
	int numSlices = (int)Math.round(angularLength) * slicesPerDegree;

	float r = 0.7f;	// default color is white (muted gray)
	float g = 0.7f;
	float b = 0.7f;
	
	public static double tx = 0;	// position (center of circle)
	public static double ty = 0;		
	public static double tz = 0;
	
	PartialDisk pdisk = new PartialDisk();
	
	public ArcObject() {
		super();
	}
	
	public void draw(Context context) {
		GL11.glPushAttrib(GL11.GL_COLOR_BUFFER_BIT);
		GL11.glColor3f(r, g, b);
		GL11.glPushMatrix();
		GL11.glTranslated(tx, ty, tz);	
		pdisk.draw(radius-width,radius,numSlices,1,startAngle,angularLength);		// (this class uses the convention in which 0deg is along the +y axis and 90deg is along the +x axis)
		GL11.glPopMatrix();
		GL11.glPopAttrib();
	}

	public int getSlicesPerDegree() {
		return slicesPerDegree;
	}

	public void setSlicesPerDegree(int slicesPerDegree) {
		this.slicesPerDegree = slicesPerDegree;
	}

	public static float getRadius() {
		return radius;
	}

	public static float getWidth() {
		return width;
	}

	public static float getStartAngle() {
		return startAngle;
	}

	public static float getAngularLength() {
		return angularLength;
	}

	public static double getTx() {
		return tx;
	}

	public static double getTy() {
		return ty;
	}

	public static double getTz() {
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
