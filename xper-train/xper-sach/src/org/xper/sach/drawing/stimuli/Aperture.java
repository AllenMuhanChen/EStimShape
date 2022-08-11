package org.xper.sach.drawing.stimuli;

public class Aperture {
	double x;
	double y;
	double z;
	double s;
	
	boolean isActive;
	
	public Aperture(double x, double y, double z, double s, boolean isActive) {
		this.x = x;
		this.y = y;
		this.z = z;
		this.s = s;
		this.isActive = isActive;
	}
	
	public Aperture() {
		this.x = 0;
		this.y = 0;
		this.z = 0;
		this.s = 1;
		this.isActive = true;
	} 
	
	public void setX(double x) {
		this.x = x;
	}
	public void setY(double y) {
		this.y = y;
	}
	public void setZ(double z) {
		this.z = z;
	}
	public void setS(double s) {
		this.s = s;
	}
	public void setIsActive(boolean isActive) {
		this.isActive = isActive;
	}
	
	public double getX() {
		return x;
	}
	public double getY() {
		return y;
	}
	public double getZ() {
		return z;
	}
	public double getS() {
		return s;
	}
	public boolean getIsActive() {
		return isActive;
	}
}
