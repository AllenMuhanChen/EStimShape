package org.xper.sach.drawing.screenobj;

import org.xper.drawing.Context;
import org.xper.drawing.Drawable;
import org.xper.drawing.RGBColor;
import org.xper.sach.renderer.SachPerspectiveRenderer;

public class OpenCircleObject implements Drawable {

	// init variables
	public static double radius1 = 80;		// units: mm? 	// if this is changed, you need to flush all to-do stimuli
	public static double radius2 = 70;
	public static double tx = 0;
	public static double ty = 0;		// if this is changed, you need to flush all to-do stimuli
	public static double tz = 0;
	
	public float r1;
	public float g1;
	public float b1;
	float r2;	// these will be set to the background colors
	float g2;
	float b2;
	
	public OpenCircleObject(float r, float g, float b) {
		this.r1 = r;
		this.g1 = g;
		this.b1 = b;
	}

	public OpenCircleObject() {
		this.r1 = 1f;	// default to white
		this.g1 = 1f;
		this.b1 = 1f;
	}

	public void draw(Context context) {
		RGBColor bkgrdColor = getBackgroundColor(context);
		this.r2 = bkgrdColor.getRed();
		this.g2 = bkgrdColor.getGreen();
		this.b2 = bkgrdColor.getBlue();

		CircleObject circ1 = new CircleObject(radius1,tx,ty,tz,r1,g1,b1);
		CircleObject circ2 = new CircleObject(radius2,tx,ty,tz,r2,g2,b2);
		
		circ1.draw(context);
		circ2.draw(context);
	}
	
	RGBColor getBackgroundColor(Context context) {
		SachPerspectiveRenderer renderer = (SachPerspectiveRenderer) context.getRenderer();
		RGBColor colors = renderer.getRgbColor();	// get background colors so that inner circle color matches
		return colors;
	}
		
	
	public float getR1() {
		return r1;
	}

	public void setR1(float r1) {
		this.r1 = r1;
	}

	public float getG1() {
		return g1;
	}

	public void setG1(float g1) {
		this.g1 = g1;
	}

	public float getB1() {
		return b1;
	}

	public void setB1(float b1) {
		this.b1 = b1;
	}

	public float getR2() {
		return r2;
	}

	public float getG2() {
		return g2;
	}

	public float getB2() {
		return b2;
	}

	public double getRadius1() {
		return radius1;
	}

	public double getRadius2() {
		return radius2;
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
}
