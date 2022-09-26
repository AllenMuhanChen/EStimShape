package org.xper.classic;

import org.xper.classic.vo.TrialContext;
import org.xper.experiment.ExperimentTask;

public interface TrialDrawingController {
	/**
	 * Before experiment start event is fired.
	 *
	 */
	public void init();

	/**
	 * When the experiment is done, after experiment stop event is fired. 
	 *
	 */
	public void destroy();

	/**
	 * Before trial start event is fired.
	 */
	public void trialStart(TrialContext context);

	public void prepareFixationOn(TrialContext context);

	public void fixationOn(TrialContext context);

	public void initialEyeInFail(TrialContext context);

	public void prepareFirstSlide(ExperimentTask task, TrialContext context);

	public void eyeInHoldFail(TrialContext context);

	public void showSlide(ExperimentTask task, TrialContext context);

	public void animateSlide(ExperimentTask task, TrialContext context);

	public void slideFinish(ExperimentTask task, TrialContext context);

	public void prepareNextSlide(ExperimentTask task, TrialContext context);

	public void eyeInBreak(TrialContext context);
	
	public void trialComplete(TrialContext context);
	
	/**
	 * Before trial stop event is fired. This happens no matter whether the trial succeeds, breaks, or fails.
	 * @param context
	 */
	public void trialStop (TrialContext context);
}
