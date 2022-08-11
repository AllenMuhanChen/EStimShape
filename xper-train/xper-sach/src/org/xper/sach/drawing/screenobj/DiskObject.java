package org.xper.sach.drawing.screenobj;

import org.lwjgl.opengl.GL11;
import org.lwjgl.util.glu.Disk;
import org.xper.drawing.Context;
import org.xper.drawing.Drawable;

public class DiskObject implements Drawable {
	
	public static float radius = 3f;//1.5f;			// when changing any static variable, you need to purge and recreate stimuli (so their targetPositions are correctly calculated)
	public static float innerRadius = 0;				
	int slicesPerDegree = 5;
	int numSlices = 360 * slicesPerDegree;

	float r = 0.8f;	// default color is white (muted gray)
	float g = 0.8f;
	float b = 0.8f;
	
	public static double tx = 0;	// position (center of circle)
	public static double ty = 80;		
	public static double tz = 0;
	
	Disk disk = new Disk();
	
	public DiskObject() {
		super();
	}
	
	public void draw(Context context) {
		GL11.glPushAttrib(GL11.GL_COLOR_BUFFER_BIT);
		GL11.glColor3f(r, g, b);
		GL11.glPushMatrix();
		GL11.glTranslated(tx, ty, tz);	
		disk.draw(innerRadius,radius,numSlices,1);		// (this class uses the convention in which 0deg is along the +y axis and 90deg is along the +x axis)
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

	public static float getInnerRadius() {
		return innerRadius;
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
