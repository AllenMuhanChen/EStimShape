package org.xper.classic;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.classic.vo.SlideTrialExperimentState;
import org.xper.classic.vo.TrialContext;
import org.xper.classic.vo.TrialResult;
import org.xper.experiment.Experiment;
import org.xper.experiment.ExperimentTask;
import org.xper.experiment.TaskDoneCache;
import org.xper.time.TimeUtil;
import org.xper.util.ThreadHelper;
import org.xper.util.TrialExperimentUtil;
import org.xper.util.XmlUtil;

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
public class SlideTrialExperiment implements Experiment {
	static Logger logger = Logger.getLogger(SlideTrialExperiment.class);

	ThreadHelper threadHelper = new ThreadHelper("SlideTrialExperiment", this);

	@Dependency
	SlideTrialExperimentState stateObject;

	public boolean isRunning() {
		return threadHelper.isRunning();
	}

	public void start() {
		threadHelper.start();
	}

	public void run() {
		TrialExperimentUtil.run(stateObject, threadHelper, new TrialRunner() {
			public TrialResult runTrial() {
				try {
					// get a task
					TrialExperimentUtil.getNextTask(stateObject);

					if (stateObject.getCurrentTask() == null && !stateObject.isDoEmptyTask()) {
						try {
							Thread.sleep(SlideTrialExperimentState.NO_TASK_SLEEP_INTERVAL);
						} catch (InterruptedException e) {
						}
						return TrialResult.NO_MORE_TASKS;
					}

					// initialize trial context
					stateObject.setCurrentContext(new TrialContext());
					stateObject.getCurrentContext().setCurrentTask(stateObject.getCurrentTask());
					TrialExperimentUtil.checkCurrentTaskAnimation(stateObject);

					// run trial
					return TrialExperimentUtil.runTrial(stateObject, threadHelper, new SlideRunner() {

						public TrialResult runSlide() {
							int slidePerTrial = stateObject.getSlidePerTrial();
							TrialDrawingController drawingController = stateObject.getDrawingController();
							ExperimentTask currentTask = stateObject.getCurrentTask();
							TrialContext currentContext = stateObject.getCurrentContext();	
							TaskDoneCache taskDoneCache = stateObject.getTaskDoneCache();
							TimeUtil globalTimeClient = stateObject.getGlobalTimeClient();
							
							try {
								for (int i = 0; i < slidePerTrial; i++) {
									
									// draw the slide
									TrialResult result = TrialExperimentUtil.doSlide(i, stateObject);
									if (result != TrialResult.SLIDE_OK) {
										return result;
									}

									// slide done successfully
									if (currentTask != null) {
										taskDoneCache.put(currentTask, globalTimeClient
												.currentTimeMicros(), false);
										currentTask = null;
										stateObject.setCurrentTask(currentTask);
									}

									// prepare next task
									if (i < slidePerTrial - 1) {
										TrialExperimentUtil.getNextTask(stateObject);
										currentTask = stateObject.getCurrentTask();
										if (currentTask == null && !stateObject.isDoEmptyTask()) {
											try {
												Thread.sleep(SlideTrialExperimentState.NO_TASK_SLEEP_INTERVAL);
											} catch (InterruptedException e) {
											}
											//return TrialResult.NO_MORE_TASKS;
											//deliver juice after complete.
											return TrialResult.TRIAL_COMPLETE;
										}
										stateObject.setAnimation(XmlUtil.slideIsAnimation(currentTask));
										currentContext.setSlideIndex(i + 1);
										currentContext.setCurrentTask(currentTask);
										drawingController.prepareNextSlide(currentTask,
												currentContext);
									}
									// inter slide interval
									result = TrialExperimentUtil.waitInterSlideInterval(stateObject, threadHelper);
									if (result != TrialResult.SLIDE_OK) {
										return result;
									}
								}
								return TrialResult.TRIAL_COMPLETE;
								// end of SlideRunner.runSlide
							} finally {
								try {
									TrialExperimentUtil.cleanupTask(stateObject);
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
						TrialExperimentUtil.cleanupTrial(stateObject);
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
	}

	public SlideTrialExperimentState getStateObject() {
		return stateObject;
	}

	public void setStateObject(SlideTrialExperimentState stateObject) {
		this.stateObject = stateObject;
	}

	public void setPause(boolean pause) {
		stateObject.setPause(pause);
	}
}
