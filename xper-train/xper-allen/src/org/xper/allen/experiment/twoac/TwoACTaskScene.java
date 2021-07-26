package org.xper.allen.experiment.twoac;

import org.xper.drawing.Context;
import org.xper.drawing.TaskScene;

public interface TwoACTaskScene extends TaskScene{
	public void setSample(TwoACExperimentTask task);
	public void setChoice(TwoACExperimentTask taks);
	public void drawSample(Context context, boolean fixation);
	public void drawChoice(Context context, boolean fixation);
}
