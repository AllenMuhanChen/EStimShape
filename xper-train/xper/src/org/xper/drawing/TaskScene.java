package org.xper.drawing;

import org.xper.classic.vo.TrialContext;
import org.xper.experiment.ExperimentTask;

public interface TaskScene {
	/**
	 * Global setting before first trial starts.
	 *
	 */
	public void initGL (int w, int h);
	
	public void setTask (ExperimentTask task);
	
	public void nextMarker ();
	
	public void drawTask (Context context, boolean fixationOn);
	
	public void drawStimulus (Context context);
	
	public void drawBlank (Context context, boolean fixationOn, boolean markerOn);

	public void trialStart(TrialContext context);

	public void trialStop(TrialContext context);

}
