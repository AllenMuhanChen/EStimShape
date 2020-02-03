package org.xper.allen.experiment;

import org.xper.allen.specs.GaussSpec;
import org.xper.experiment.StimSpecGenerator;


public class GaussianSpecGenerator{
	int XCenter = 0;
	int YCenter = 0;
	int Size = 100;
	int Orientation = (int) (Math.random() * Math.PI);
	int Frequency = 0;
	int Phase = (int) Math.PI;
	boolean Animation = true;
	
	public GaussSpec generate() {
		GaussSpec g = new GaussSpec();
		g.setXCenter(XCenter);
		g.setYCenter(YCenter);
		g.setSize(Size);
		g.setOrientation(Orientation);
		g.setFrequency(Frequency);
		g.setPhase(Phase);
		g.setAnimation(Animation);
		return g;
	}
	

	public String generateStimSpec() {
		return this.generate().toXml();
	}

	public void reset() { //There may be a better way of doing this, but this will reset the variables to their defaults.
		XCenter = 0;
		YCenter = 0;
		Size = 100;
		Orientation = (int) (Math.random() * Math.PI);
		Frequency = 0;
		Phase = (int) Math.PI;
		Animation = true;
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


	public int getOrientation() {
		return Orientation;
	}


	public void setOrientation(int orientation) {
		Orientation = orientation;
	}


	public int getFrequency() {
		return Frequency;
	}


	public void setFrequency(int frequency) {
		Frequency = frequency;
	}


	public int getPhase() {
		return Phase;
	}


	public void setPhase(int phase) {
		Phase = phase;
	}


	public boolean isAnimation() {
		return Animation;
	}


	public void setAnimation(boolean animation) {
		Animation = animation;
	}
}
