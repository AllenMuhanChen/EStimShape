package org.xper.allen.app.blockGenerators;

import org.xper.allen.specs.GaussSpec;

import com.thoughtworks.xstream.XStream;

public class VisualTrial {
	GaussSpec gaussSpec;
	double targetEyeWinsize;
	double duration;
	String data;
	
	transient XStream s = new XStream();
	
	public VisualTrial(GaussSpec gaussSpec, double duration, double targetEyeWinsize, String data) {
		this.gaussSpec = gaussSpec;
		this.duration = duration;
		this.targetEyeWinsize = targetEyeWinsize;
		this.data = data;
		s.alias("VisualTrial", VisualTrial.class);
		s.setMode(XStream.NO_REFERENCES);
	}
	
	public String toXml() {
		return s.toXML(this);
	}
	
	public double getDuration() {
		return duration;
	}

	public void setDuration(double duration) {
		this.duration = duration;
	}

	public GaussSpec getGaussSpec() {
		return gaussSpec;
	}

	public void setGaussSpec(GaussSpec gaussSpec) {
		this.gaussSpec = gaussSpec;
	}

	public double getTargetEyeWinsize() {
		return targetEyeWinsize;
	}

	public void setTargetEyeWinsize(double targetEyeWinsize) {
		this.targetEyeWinsize = targetEyeWinsize;
	}

	public String getData() {
		return data;
	}

	public void setData(String data) {
		this.data = data;
	}
}
