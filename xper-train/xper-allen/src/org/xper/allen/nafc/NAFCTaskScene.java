package org.xper.allen.nafc;

import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.drawing.Context;
import org.xper.drawing.TaskScene;

public interface NAFCTaskScene extends TaskScene{
	public void setSample(NAFCExperimentTask task);
	public void setChoice(NAFCExperimentTask taks);
	public void drawSample(Context context, boolean fixation);
	public void drawChoice(Context context, boolean fixation);
}
