package org.xper.allen.nafc.experiment;

import org.xper.Dependency;
import org.xper.allen.nafc.NAFCTaskScene;
import org.xper.classic.MarkStimTrialDrawingController;
import org.xper.classic.TrialDrawingController;
import org.xper.classic.vo.TrialContext;
import org.xper.drawing.Context;
import org.xper.experiment.ExperimentTask;
import org.xper.time.DefaultTimeUtil;
import org.xper.time.TimeUtil;
import org.xper.util.ThreadUtil;

public class NAFCMarkStimTrialDrawingController extends MarkStimTrialDrawingController implements NAFCTrialDrawingController{

	@Dependency
	protected NAFCTaskScene taskScene;
	boolean initialized = false;

	TimeUtil timeUtil = new DefaultTimeUtil();
	private long lastTime = 0;
	private int skippedFrames = 0;
	@Override
	public void slideFinish(ExperimentTask task, TrialContext context) {
		taskScene.nextMarker();
		taskScene.drawBlank(context, false, false);
		window.swapBuffers();
	}

	public void prepareSample(NAFCExperimentTask task, Context context) {
		if (task != null) {
			taskScene.setSample(task);
			taskScene.drawSample(context, true);
		} else {
			taskScene.drawBlank(context, false, false);
		}
	}

	public void prepareChoice(NAFCExperimentTask task, Context context) {
		if (task != null) {
			taskScene.setChoice(task);
			taskScene.drawChoice(context, false);
		} else {
			taskScene.drawBlank(context, false, false);
		}
	}

	public NAFCTaskScene getNAFCTaskScene() {
		return taskScene;
	}

	public void setTaskScene(NAFCTaskScene taskScene) {
		this.taskScene = taskScene;
	}

	// not sure if below needed. 
	public void init() {
		window.create();
		taskScene.initGL(window.getWidth(), window.getHeight());
		initialized = true;
	}

	public void destroy() {
		if (initialized) {
			window.destroy();
			initialized = false;
		}
	}

	public void animateSample(NAFCExperimentTask task, Context context) {
		if(task!=null) {
			long startTime = timeUtil.currentTimeMicros();
			taskScene.drawSample(context, true);
			System.out.println("AC TIME TO DRAW SAMPLE: " + (timeUtil.currentTimeMicros() - startTime));
			//			System.out.println("ANIMATE SAMPLE CALLED!");

		} else {
			taskScene.drawBlank(context, fixationOnWithStimuli, true);
		}
		window.swapBuffers();
		long nowTime = timeUtil.currentTimeMicros();
		long frameTime=0;
		if(lastTime!=0) {
			frameTime = nowTime-lastTime;
		}

		System.out.println("AC MICROS SINCE LAST BUFFER SWAP: " + frameTime);
		lastTime = nowTime;
		if(frameTime>18000) {
			int temp = Math.round(frameTime/16666);
			skippedFrames = skippedFrames + temp;
		}
		System.out.println("AC TOTAL SKIPPED FRAMES: " + skippedFrames);
	}

}
