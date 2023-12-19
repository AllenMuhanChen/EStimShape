package org.xper.classic;

import org.xper.Dependency;
import org.xper.classic.vo.TrialContext;
import org.xper.drawing.Context;
import org.xper.drawing.TaskScene;
import org.xper.drawing.Window;
import org.xper.experiment.ExperimentTask;

public class MarkStimTrialDrawingController implements TrialDrawingController {
	@Dependency
	private Window window;
	@Dependency
	protected TaskScene taskScene;
	@Dependency
	protected boolean fixationOnWithStimuli = true;

	boolean initialized = false;

	protected void drawTaskScene(ExperimentTask task, Context context) {
		if (task != null) {
			getTaskScene().setTask(task);
			getTaskScene().drawTask(context, fixationOnWithStimuli);
		} else {
			getTaskScene().drawBlank(context, fixationOnWithStimuli, true);
		}
	}

	protected void animateTaskScene(ExperimentTask task, Context context) {
		if (task != null) {
			getTaskScene().drawTask(context, fixationOnWithStimuli);
		} else {
			getTaskScene().drawBlank(context, fixationOnWithStimuli, true);
		}
	}

	public void init() {
		getWindow().create();
		getTaskScene().initGL(getWindow().getWidth(), getWindow().getHeight());

		initialized = true;

		getTaskScene().drawBlank(new Context(), false, false);
		getWindow().swapBuffers();
	}

	public void destroy() {
		if (initialized) {
			getWindow().destroy();
			initialized = false;
		}
	}

	public void trialStart(TrialContext context) {
		getTaskScene().trialStart(context);
	}

	public void prepareFixationOn(TrialContext context) {
		getTaskScene().drawBlank(context, true, false);
	}

	public void fixationOn(TrialContext context) {
		getWindow().swapBuffers();
	}

	public void initialEyeInFail(TrialContext context) {
		getTaskScene().drawBlank(context, false, false);
		getWindow().swapBuffers();
	}

	public void prepareFirstSlide(ExperimentTask task, TrialContext context) {
		getTaskScene().nextMarker();
		drawTaskScene(task, context);
	}

	public void eyeInHoldFail(TrialContext context) {
		getTaskScene().drawBlank(context, false, false);
		getWindow().swapBuffers();
	}

	public void showSlide(ExperimentTask task, TrialContext context) {
		getWindow().swapBuffers();
	}

	public void animateSlide(ExperimentTask task, TrialContext context) {
		animateTaskScene(task, context);
		getWindow().swapBuffers();
	}

	public void slideFinish(ExperimentTask task, TrialContext context) {
		getTaskScene().drawBlank(context, true, false);
		getWindow().swapBuffers();
	}

	public void prepareNextSlide(ExperimentTask task, TrialContext context) {
		getTaskScene().nextMarker();
		drawTaskScene(task, context);
	}

	public void eyeInBreak(TrialContext context) {
		getTaskScene().drawBlank(context, false, false);
		getWindow().swapBuffers();
	}

	public Window getWindow() {
		return window;
	}

	public void setWindow(Window window) {
		this.window = window;
	}

	public TaskScene getTaskScene() {
		return taskScene;
	}

	public void setTaskScene(TaskScene taskScene) {
		this.taskScene = taskScene;
	}

	public void trialComplete(TrialContext context) {
		getTaskScene().drawBlank(context, false, false);
		getWindow().swapBuffers();
	}

	public void trialStop(TrialContext context) {
		getTaskScene().trialStop(context);
	}

	public boolean isFixationOnWithStimuli() {
		return fixationOnWithStimuli;
	}

	public void setFixationOnWithStimuli(boolean fixationOnWithStimuli) {
		this.fixationOnWithStimuli = fixationOnWithStimuli;
	}
}