package org.xper.allen.blockgen;

import org.xper.allen.specs.EStimObjData;
import org.xper.allen.specs.GaussSpec;
import org.xper.drawing.Coordinates2D;

import com.thoughtworks.xstream.XStream;

public class VEStimTrial {
	EStimObjData eStimSpec;
	GaussSpec gaussSpec;
	Coordinates2D targetEyeWinCoords;
	double targetEyeWinSize;
	double duration;
	String data;
	
	transient XStream s = new XStream();
	
	public VEStimTrial(EStimObjData eStimSpec, GaussSpec gaussSpec, Coordinates2D targetEyeWinCoords, double targetEyewinSize, double duration, String data) {
		this.eStimSpec = eStimSpec;
		this.gaussSpec = gaussSpec;
		this.targetEyeWinCoords = targetEyeWinCoords;
		this.duration = duration;
		this.data = data;
	}
	
	public String toXml() {
		return s.toXML(this);
	}

	public EStimObjData getEStimSpec() {
		return eStimSpec;
	}

	public void setEStimSpec(EStimObjData eStimSpec) {
		this.eStimSpec = eStimSpec;
	}

	public GaussSpec getGaussSpec() {
		return gaussSpec;
	}

	public void setGaussSpec(GaussSpec gaussSpec) {
		this.gaussSpec = gaussSpec;
	}

	public Coordinates2D getTargetEyeWinCoords() {
		return targetEyeWinCoords;
	}

	public void setTargetEyeWinCoords(Coordinates2D targetEyeWinCoords) {
		this.targetEyeWinCoords = targetEyeWinCoords;
	}

	public double getTargetEyeWinSize() {
		return targetEyeWinSize;
	}

	public void setTargetEyeWinSize(double targetEyeWinSize) {
		this.targetEyeWinSize = targetEyeWinSize;
	}

	public double getDuration() {
		return duration;
	}

	public void setDuration(double duration) {
		this.duration = duration;
	}

	public String getData() {
		return data;
	}

	public void setData(String data) {
		this.data = data;
	}
}

