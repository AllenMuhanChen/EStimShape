package org.xper.sach.drawing.stimuli;

import org.xper.drawing.RGBColor;
import org.xper.sach.drawing.splines.MyPoint;

public class Occluder {
	MyPoint leftBottom;
	MyPoint rightTop; 
	RGBColor color;
	
	public Occluder(double[] leftBottom, double[] rightTop, RGBColor color) {
		this.leftBottom.x = leftBottom[0];
		this.leftBottom.y = leftBottom[1];
		this.leftBottom.z = leftBottom[2];
		this.rightTop.x = rightTop[0];
		this.rightTop.y = rightTop[1];
		this.rightTop.z = rightTop[2];
		this.color = color;
	}
	
	public Occluder() {
		this.leftBottom = new MyPoint(-10,-10,10);
		this.rightTop = new MyPoint(10,10,10);
		this.color = new RGBColor();
	}
	
	public void setLeftBottom(MyPoint lb) {
		this.leftBottom = lb;
	}
	public void setRightTop(MyPoint rt) {
		this.rightTop = rt;
	}
	public void setColor(RGBColor color) {
		this.color = color;
	}
	
	public MyPoint getLeftBottom() {
		return leftBottom;
	}
	public MyPoint getRightTop() {
		return rightTop;
	}
	public RGBColor getColor() {
		return color;
	}
}
