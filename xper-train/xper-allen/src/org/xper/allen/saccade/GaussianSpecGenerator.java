package org.xper.allen.saccade;

import org.xper.allen.specs.GaussSpec;

public class GaussianSpecGenerator{
	int XCenter = 0;
	int YCenter = 0;
	int Size = 100;
	double Brightness = 1.0;
	
	public GaussSpec generate() {
		GaussSpec g = new GaussSpec();
		g.setXCenter(XCenter);
		g.setYCenter(YCenter);
		g.setSize(Size);
		g.setBrightness(Brightness);
		return g;
	}
	

	public String generateStimSpec() {
		return this.generate().toXml();
	}

	public void reset() { //There may be a better way of doing this, but this will reset the variables to their defaults.
		XCenter = 0;
		YCenter = 0;
		Size = 100;
		Brightness = 1.0;
	}
	
	public int getXCenter() {
		return XCenter;
	}


	public void setXCenter(int xCenter) {
		XCenter = xCenter;
	}


	public int getYCenter() {
		return YCenter;
	}


	public void setYCenter(int yCenter) {
		YCenter = yCenter;
	}


	public int getSize() {
		return Size;
	}


	public void setSize(int size) {
		Size = size;
	}
}
