package org.xper.allen.experiment.saccade;

import java.util.List;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.allen.util.AllenDbUtil;
import org.xper.classic.SlideRunner;
import org.xper.classic.TrialEventListener;
import org.xper.classic.TrialRunner;
import org.xper.classic.vo.SlideTrialExperimentState;
import org.xper.classic.vo.TrialResult;
import org.xper.drawing.Coordinates2D;
import org.xper.experiment.Experiment;
import org.xper.experiment.TaskDoneCache;
import org.xper.eye.EyeMonitor;
import org.xper.time.TimeUtil;
import org.xper.util.IntanUtil;
import org.xper.util.ThreadHelper;
import org.xper.util.TrialExperimentUtil;

import jssc.SerialPortException;

import org.xper.allen.experiment.saccade.SaccadeExperimentState;

/**
 * Format of StimSpec:
 * 
 * <StimSpec animation="true"> ... </StimSpec>
 * 
 * If attribute animation is false or missing, the stimulus is treated as a
 * static slide.
 * 
 * @author wang
 * 
 */
public class SaccadeTrialExperiment implements Experiment {
	static Logger logger = Logger.getLogger(SaccadeTrialExperiment.class);

	ThreadHelper threadHelper = new ThreadHelper("SaccadeTrialExperiment", this);
	@Dependency
	EyeMonitor eyeMonitor;
	@Dependency
	SaccadeExperimentState stateObject;
	@Dependency
	AllenDbUtil dbUtil;


	@Dependency
	int blankTargetScreenDisplayTime; //in ms
	
	public boolean isRunning() {
		return threadHelper.isRunning();
	}

	public void start() {
		threadHelper.start();
	}

	public void run() {
		SaccadeTrialExperimentUtil.run(stateObject, threadHelper, new TrialRunner() {
			public TrialResult runTrial() {
				try {
					// get a task
					SaccadeTrialExperimentUtil.getNextTask(stateObject);

					if (stateObject.getCurrentTask() == null && !stateObject.isDoEmptyTask()) {
						try {
							Thread.sleep(SlideTrialExperimentState.NO_TASK_SLEEP_INTERVAL);
						} catch (InterruptedException e) {
						}
						return TrialResult.NO_MORE_TASKS;
					}

					// initialize trial context
					SaccadeTrialContext context = new SaccadeTrialContext();
					context.setCurrentTask(stateObject.getCurrentTask());
					stateObject.setCurrentContext(context);
					stateObject.getCurrentContext().setCurrentTask(stateObject.getCurrentTask());
					/*
					TrialExperimentUtil.checkCurrentTaskAnimation(stateObject);
					*/
					

					
					// run trial
					return SaccadeTrialExperimentUtil.runTrial(stateObject, threadHelper, new SlideRunner() { //TODO: Possibly 		ret = TrialExperimentUtil.runTrial(stateObject, threadHelper, new SlideRunner() {

						public TrialResult runSlide() {
							int slidePerTrial = stateObject.getSlidePerTrial();
							SaccadeExperimentTask currentTask = (SaccadeExperimentTask) stateObject.getCurrentTask();
							TaskDoneCache taskDoneCache = stateObject.getTaskDoneCache();
							TimeUtil globalTimeClient = stateObject.getGlobalTimeClient();
							List<? extends TrialEventListener> trialEventListeners = stateObject.getTrialEventListeners();
							TrialResult result;
							
							try {
								try {
									//target info -AC
									Coordinates2D targetPosition = context.getCurrentTask().getTargetEyeWinCoords();
									double targetEyeWinSize = context.getCurrentTask().getTargetEyeWinSize();
									context.setTargetPos(targetPosition);
									context.setTargetEyeWindowSize(targetEyeWinSize);
								} catch (Exception e){
									System.out.println("No More Trials");
									try {
										Thread.sleep(SaccadeTrialExperimentState.NO_TASK_SLEEP_INTERVAL);
									} catch (InterruptedException ie) {
									}
									return TrialResult.NO_MORE_TASKS;
								}

								for (int i = 0; i < slidePerTrial; i++) {
									
									// draw the slide
									result = SaccadeTrialExperimentUtil.doSlide(i, stateObject);
									
									
									// Trial done successfully
									if (currentTask != null) {
										taskDoneCache.put(currentTask, globalTimeClient
												.currentTimeMicros(), false);
										currentTask = null;
										stateObject.setCurrentTask(currentTask);
										
									}

								}
								return TrialResult.TRIAL_COMPLETE;
								// end of SlideRunner.runSlide
							} finally {
								try {
									SaccadeTrialExperimentUtil.cleanupTask(stateObject);
								} catch (Exception e) {
									logger.warn(e.getMessage());
									e.printStackTrace();
								}
							}
						}
						
					}); // end of TrialExperimentUtil.runTrial 
					// end of TrialRunner.runTrial	
				} finally {
					try {
						SaccadeTrialExperimentUtil.cleanupTrial(stateObject);
					} catch (Exception e) {
						logger.warn(e.getMessage());
						e.printStackTrace();
					}
				}
			}}
		);
	}

	public void stop() {
		System.out.println("Stopping SlideTrialExperiment ...");
		if (isRunning()) {
			threadHelper.stop();
			threadHelper.join();
		}
		try {
			System.out.println("SHUTTING DOWN SERIAl PORT");
			stateObject.getIntanUtil().shutdown();
			System.out.println("SERIAL PORT SHUT DOWN");
		} catch (SerialPortException e) {
			e.printStackTrace();
		}
	}

	public SaccadeExperimentState getStateObject() {
		return stateObject;
	}

	public void setStateObject(SaccadeExperimentState stateObject) {
		this.stateObject = stateObject;
	}

	public void setPause(boolean pause) {
		stateObject.setPause(pause);
	}

	public int getBlankTargetScreenDisplayTime() {
		return blankTargetScreenDisplayTime;
	}

	public void setBlankTargetScreenDisplayTime(int blankTargetScreenDisplayTime) {
		this.blankTargetScreenDisplayTime = blankTargetScreenDisplayTime;
	}

	public AllenDbUtil getDbUtil() {
		return dbUtil;
	}

	public void setDbUtil(AllenDbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}
	public EyeMonitor getEyeMonitor() {
		return eyeMonitor;
	}
	public void setEyeMonitor(EyeMonitor eyeMonitor) {
		this.eyeMonitor = eyeMonitor;
	}


}
