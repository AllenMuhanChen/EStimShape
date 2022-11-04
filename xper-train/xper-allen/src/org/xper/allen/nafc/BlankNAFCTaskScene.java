package org.xper.allen.nafc;

import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.allen.nafc.experiment.NAFCTrialContext;
import org.xper.drawing.AbstractTaskScene;
import org.xper.drawing.Context;
import org.xper.experiment.ExperimentTask;

public class BlankNAFCTaskScene extends AbstractTaskScene implements NAFCTaskScene{
	public void trialStart(NAFCTrialContext context) {
		
	}
	
	public void drawStimulus(Context context) {
	}

	public void setTask(ExperimentTask task) {
	}

	@Override
	public void setSample(NAFCExperimentTask task) {
		// TODO Auto-generated method stub
		
	}

	@Override
	public void setChoice(NAFCExperimentTask taks) {
		// TODO Auto-generated method stub
		
	}

	@Override
	public void drawSample(Context context, boolean fixation) {
		// TODO Auto-generated method stub
		
	}

	@Override
	public void drawChoices(Context context, boolean fixation) {
		// TODO Auto-generated method stub
		
	}

	@Override
	public void drawChoice(Context context, boolean fixationOn, int i) {

	}

}
