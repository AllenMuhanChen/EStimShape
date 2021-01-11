package org.xper.allen.experiment.twoac;

import org.xper.allen.db.vo.EStimObjDataEntry;
import org.xper.allen.specs.GaussSpec;
import org.xper.drawing.Coordinates2D;
import org.xper.experiment.ExperimentTask;

/**
 * Holds information that goes to both the drawing controller (in the form of a string XML. It is the job of the Graphics Object to decode this, like RFPlotGaussianObject)
 * and the rest of the code. 
 * @author allenchen
 *
 */
public class TwoACExperimentTask extends ExperimentTask {
	
	Coordinates2D[] targetEyeWinCoords;
	double[] targetEyeWinSize;
	//double[] duration;
	EStimObjDataEntry eStimObjDataEntry;
	
	String sampleSpec;
	String[] choiceSpec;
	
	public String getSampleSpec() {
		return sampleSpec;
	}

	public void setSampleSpec(String sampleSpec) {
		this.sampleSpec = sampleSpec;
	}

	public String[] getChoiceSpec() {
		return choiceSpec;
	}

	public void setChoiceSpec(String[] choiceSpec) {
		this.choiceSpec = choiceSpec;
	}

	/*
	public Coordinates2D parseCoords() {
		GaussSpec g = GaussSpec.fromXml(this.getStimSpec());
		Coordinates2D coords = new Coordinates2D(g.getXCenter(),g.getYCenter());
		return coords;
	}
	*/
	public Coordinates2D[] getTargetEyeWinCoords() {
		return targetEyeWinCoords;
	}

	public void setTargetEyeWinCoords(Coordinates2D[] targetEyeWinCoords) {
		this.targetEyeWinCoords = targetEyeWinCoords;
	}
	
	public double[] getTargetEyeWinSize() {
		return targetEyeWinSize;
	}

	public void setTargetEyeWinSize(double[] targetEyeWinSize) {
		this.targetEyeWinSize = targetEyeWinSize;
	}
/*
	public void setDuration(double[] duration) {
		this.duration = duration;
	}

	public double[] getDuration() {
		return duration;
	}
*/
	public EStimObjDataEntry geteStimObjDataEntry() {
		return eStimObjDataEntry;
	}

	public void seteStimObjDataEntry(EStimObjDataEntry eStimObjDataEntry) {
		this.eStimObjDataEntry = eStimObjDataEntry;
	}
	
	

}
