package org.xper.allen.nafc.experiment;

import org.xper.Dependency;
import org.xper.allen.nafc.NAFCTaskScene;
import org.xper.classic.MarkStimTrialDrawingController;
import org.xper.experiment.ExperimentTask;
import org.xper.time.DefaultTimeUtil;
import org.xper.time.TimeUtil;

public class NAFCMarkStimTrialDrawingController extends MarkStimTrialDrawingController implements NAFCTrialDrawingController{

	@Dependency
	private NAFCTaskScene taskScene;
	boolean initialized = false;

	//TIMING ANALYSIS
	boolean showTiming = false;
	TimeUtil timeUtil = new DefaultTimeUtil();
	private long lastTime = 0;
	private int skippedFrames = 0;
	private long startTime=0;

	public void trialStart(NAFCTrialContext context) {
		getTaskScene().trialStart(context);

		getTaskScene().nextMarker();
		getTaskScene().drawBlank(context, false, false);
		getWindow().swapBuffers();
	}

	/////////////////
	public void slideFinish(ExperimentTask task, NAFCTrialContext context) {
		getTaskScene().nextMarker();
		getTaskScene().drawBlank(context, false, false);
		getWindow().swapBuffers();
		startTime=0;
	}

	public void prepareSample(NAFCExperimentTask task, NAFCTrialContext context) {
		if (task != null) {
			getTaskScene().setSample(task);
		}
	}

	public void showSample(NAFCExperimentTask task, NAFCTrialContext context) {
		if(task != null) {
			getTaskScene().drawSample(context, true);
		} else {
			getTaskScene().drawBlank(context, false, false);
		}
		getWindow().swapBuffers();
	}

	@Override
	public void showAnswer(NAFCExperimentTask task, NAFCTrialContext context) {
		int[] correct = task.getRewardList();
		if(task != null) {
			getTaskScene().drawChoice(context, false, correct[0]);
		} else {
			getTaskScene().drawBlank(context, false, false);
		}
		getWindow().swapBuffers();

	}


	public void prepareChoice(NAFCExperimentTask task, NAFCTrialContext context) {
		if (task != null) {
			getTaskScene().setChoice(task);
		}
	}

	public void showChoice(NAFCExperimentTask task, NAFCTrialContext context) {
		if(task != null) {
			getTaskScene().drawChoices(context, false);
		} else {
			getTaskScene().drawBlank(context, false, false);
		}
		getWindow().swapBuffers();
	}

	public NAFCTaskScene getNAFCTaskScene() {
		return getTaskScene();
	}

	public void setTaskScene(NAFCTaskScene taskScene) {
		this.taskScene = taskScene;
	}

	// not sure if below needed. 
	public void init() {
		getWindow().create();
		getTaskScene().initGL(getWindow().getWidth(), getWindow().getHeight());
		initialized = true;
	}

	public void destroy() {
		if (initialized) {
			getWindow().destroy();
			initialized = false;
		}
	}

//	public void animateSample(NAFCExperimentTask task, NAFCTrialContext context) {
//		if(task!=null) {
//			getTaskScene().drawBlank(context, fixationOnWithStimuli, true);
//		} else {
//			
//		}
//		getWindow().swapBuffers();
//		if(showTiming) {
//			long nowTime = timeUtil.currentTimeMicros();
//			if(startTime==0) {
//				startTime = nowTime;
//			}
//			long frameTime=0;
//			if(lastTime!=0) {
//				frameTime = nowTime-lastTime;
//			}
//
//			System.out.println("AC MICROS SINCE LAST BUFFER SWAP: " + frameTime);
//			lastTime = nowTime;
//			if(frameTime>18000) {
//				int temp = Math.round(frameTime/16666);
//				skippedFrames = skippedFrames + temp;
//			}
//
//			System.out.println("AC TOTAL SKIPPED FRAMES: " + skippedFrames);
//			long timeElapsed = nowTime - startTime;
//
//			System.out.println("OVER: " + timeElapsed/1000000 + " seconds");
//		}
//	}
//	
	public void animateSample(NAFCExperimentTask task, NAFCTrialContext context) {
		if(task!=null) {
			long startTime = timeUtil.currentTimeMicros();
			getTaskScene().drawSample(context, true);
			if(showTiming)
				System.out.println("AC TIME TO DRAW SAMPLE: " + (timeUtil.currentTimeMicros() - startTime));
			//			System.out.println("ANIMATE SAMPLE CALLED!");

		} else {
			getTaskScene().drawBlank(context, fixationOnWithStimuli, true);
		}
		getWindow().swapBuffers();
		if(showTiming) {
			long nowTime = timeUtil.currentTimeMicros();
			if(startTime==0) {
				startTime = nowTime;
			}
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
			long timeElapsed = nowTime - startTime;

			System.out.println("OVER: " + timeElapsed/1000000 + " seconds");
		}
	}
	//		System.out.println("MAX TEXTURES: " + GL11.GL_MAX_TEXTURE_STACK_DEPTH);

	public NAFCTaskScene getTaskScene() {
		return taskScene;
	}

}
