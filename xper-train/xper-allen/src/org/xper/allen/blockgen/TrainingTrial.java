package org.xper.allen.blockgen;

import org.xper.allen.db.vo.EStimObjDataEntry;
import org.xper.allen.specs.EStimObjData;
import org.xper.allen.specs.GaussSpec;
import org.xper.drawing.Coordinates2D;

import com.thoughtworks.xstream.XStream;

/**
 * Class to make initializing a StimSpec intended for purely visual stimuli easier. 
 * @author allenchen
 *
 */
public class TrainingTrial implements Trial {
	GaussSpec gaussSpec;
	Coordinates2D targetEyeWinCoords;
	double targetEyeWinSize;
	double duration;
	String data;
	
	transient XStream s = new XStream();
	/**
	 * 
	 * @param gaussSpec
	 * @param duration
	 * @param targetEyeWinCoords
	 * @param targetEyeWinsize
	 * @param data
	 */
	public TrainingTrial(GaussSpec gaussSpec, double duration, Coordinates2D targetEyeWinCoords, double targetEyeWinsize, String data) {
		this.gaussSpec = gaussSpec;
		this.duration = duration;
		this.targetEyeWinCoords = targetEyeWinCoords;
		this.targetEyeWinSize = targetEyeWinsize;
		this.data = data;
		s.alias("VisualTrial", TrainingTrial.class);
		s.setMode(XStream.NO_REFERENCES);
	}
	
	public TrainingTrial() {
		
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

	public double getTargetEyeWinSize() {
		return targetEyeWinSize;
	}

	public void setTargetEyeWinsize(double targetEyeWinsize) {
		this.targetEyeWinSize = targetEyeWinsize;
	}

	public String getData() {
		return data;
	}

	public void setData(String data) {
		this.data = data;
	}

	public Coordinates2D getTargetEyeWinCoords() {
		return targetEyeWinCoords;
	}

	public void setTargetEyeWinCoords(Coordinates2D targetEyeWinCoords) {
		this.targetEyeWinCoords = targetEyeWinCoords;
	}

	@Override
	public EStimObjDataEntry getEStimSpec() {
		// TODO Auto-generated method stub
		return null;
	}
}
