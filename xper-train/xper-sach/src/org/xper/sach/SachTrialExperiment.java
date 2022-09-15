package org.xper.sach;


import java.util.List;

import org.apache.log4j.Logger;
import org.dom4j.Node;
import org.xper.Dependency;
import org.xper.classic.SlideRunner;
import org.xper.classic.TrialDrawingController;
import org.xper.classic.TrialEventListener;
import org.xper.classic.TrialRunner;
import org.xper.classic.vo.SlideTrialExperimentState;
import org.xper.classic.vo.TrialResult;
import org.xper.drawing.Coordinates2D;
import org.xper.exception.XmlDocInvalidFormatException;
import org.xper.experiment.Experiment;
import org.xper.experiment.ExperimentTask;
import org.xper.experiment.TaskDoneCache;
import org.xper.eye.EyeMonitor;
//import org.xper.eye.EyeTargetSelector;
import org.xper.sach.util.SachEventUtil;
import org.xper.sach.util.SachExperimentUtil;
import org.xper.sach.util.SachXmlUtil;
import org.xper.sach.vo.SachExperimentState;
import org.xper.sach.vo.SachTrialContext;
import org.xper.time.TimeUtil;
import org.xper.util.ThreadHelper;
import org.xper.util.TrialExperimentUtil;
import org.xper.util.XmlUtil;


/**
 * Format of StimSpec:
 * 
 * 
 * <StimSpec> 
 * 	<object animation="false"> ... </object> 
 * 	<object animation="false"> ... </object> 
 *  ... (one to ten objects)
 * 	<object animation="false"> ... </object>
 *  <targetPosition>...</targetPosition>
 *  <targetEyeWinSize>...</targetEyeWinSize>
 *  <targetIndex>...</targetIndex>
 *  <reward>...</reward>
 * </StimSpec>
 * 
 * If attribute animation is false or missing, the object is treated as a static
 * slide.
 * 
 * @author wang
 * 
 */

public class SachTrialExperiment implements Experiment {
	static Logger logger = Logger.getLogger(SachTrialExperiment.class);

	@Dependency
	SachExperimentState stateObject;
	
	@Dependency
	EyeMonitor eyeMonitor;
	
	@Dependency
	int firstSlideISI;
	
	@Dependency
	int firstSlideLength;
	
	@Dependency
	int blankTargetScreenDisplayTime; // in milliseconds
	
	@Dependency
	int earlyTargetFixationAllowableTime; // in milliseconds
	
	ThreadHelper threadHelper = new ThreadHelper("SachExperiment", this);
	
	public boolean isRunning() {
		return threadHelper.isRunning();
	}

	public void start() {
		threadHelper.start();
	}

	public void run() {
		TrialExperimentUtil.run(stateObject, threadHelper, new TrialRunner() {

			public TrialResult runTrial() {
				TrialResult ret = TrialResult.INITIAL_EYE_IN_FAIL;
				try {
					// get a task
					TrialExperimentUtil.getNextTask(stateObject);

					if (stateObject.getCurrentTask() == null) {
						try {
							Thread.sleep(SlideTrialExperimentState.NO_TASK_SLEEP_INTERVAL);
						} catch (InterruptedException e) {
						}
						return TrialResult.NO_MORE_TASKS;
					}
					
					// parse and save the doc object for later use.
					stateObject.setCurrentSpecDoc(XmlUtil.parseSpec(stateObject.getCurrentTask().getStimSpec()));

					// initialized context
					SachTrialContext context = new SachTrialContext();
					context.setCurrentTask(stateObject.getCurrentTask());	// add current task to context!
					stateObject.setCurrentContext(context);
					
					final List<?> objectNodeList = stateObject.getCurrentSpecDoc().selectNodes("/StimSpec/object");
					final int countObject = objectNodeList.size();
					if (countObject == 0) {
						throw new XmlDocInvalidFormatException("No objects in match task specification.");
					}
					context.setCountObjects(countObject);
					if (logger.isDebugEnabled()) {
						logger.debug(stateObject.getCurrentTask().getTaskId() + " " + countObject);
					}

					// target info -shs
					Coordinates2D targetPosition = new Coordinates2D(0, 0); // SachXmlUtil.getTargetPosition(stateObject.getCurrentSpecDoc());
					double targetEyeWinSize = 0; //SachXmlUtil.getTargetEyeWinSize(stateObject.getCurrentSpecDoc());
					long targetIndex = 0; // SachXmlUtil.getTargetIndex(stateObject.getCurrentSpecDoc());
					context.setTargetPos(targetPosition);
					context.setTargetEyeWindowSize(targetEyeWinSize);
					context.setTargetIndex(targetIndex);

					// reward info -shs
					long reward = SachXmlUtil.getReward(stateObject.getCurrentSpecDoc());
					context.setReward(reward);
					
					// first object animated?
					Node objectNode = (Node)objectNodeList.get(0);
//					stateObject.setAnimation(XmlUtil.isAnimation(objectNode));

//					SachExperimentUtil.playSingleNote(50,100);
//					SachExperimentUtil.playSingleNote(50,100);
					// runModeRun task
					ret = TrialExperimentUtil.runTrial(stateObject,
							threadHelper, new SlideRunner() {

						public TrialResult runSlide() {
							TrialDrawingController drawingController = stateObject.getDrawingController();
							ExperimentTask currentTask = stateObject.getCurrentTask();
							SachTrialContext currentContext = (SachTrialContext) stateObject.getCurrentContext();
							TaskDoneCache taskDoneCache = stateObject.getTaskDoneCache();
							TimeUtil globalTimeClient = stateObject.getGlobalTimeClient();
							TimeUtil timeUtil = stateObject.getLocalTimeUtil();
//							EyeTargetSelector targetSelector = stateObject.getTargetSelector();
							List<? extends TrialEventListener> trialEventListeners = stateObject.getTrialEventListeners();
							TrialResult result = TrialResult.FIXATION_SUCCESS;

							try {
								//int interSlideInterval = stateObject.getInterSlideInterval();
								//int slideLength = stateObject.getSlideLength();
								for (int i = 0; i < countObject; i++) {
									
									//if (i == 0) {			// ***commented out: now always using regular values for all slides
									//	stateObject.setInterSlideInterval(firstSlideISI);
									//	stateObject.setSlideLength(firstSlideLength);
									//} else {
									//	stateObject.setInterSlideInterval(interSlideInterval);
									//	stateObject.setSlideLength(slideLength);
									//}
									
									// show first slide, it's already draw in drawingController while waiting for monkey fixation
									result = TrialExperimentUtil.doSlide(i, stateObject);

									if (result != TrialResult.SLIDE_OK) {
//										if (false) {
//											// SachExperimentUtil.isTargetOn(currentContext) && currentContext.getTargetIndex() >= 0
//											if (earlyTargetFixationAllowableTime < 0) {
//												// ok to break fixation
//											} else {
//												long currentTime = timeUtil.currentTimeMicros();
//												long earliestTime = currentContext.getCurrentSlideOnTime() + stateObject.getSlideLength() * 1000 - 
//														earlyTargetFixationAllowableTime * 1000;
//												if (currentTime >= earliestTime) {
//													// ok to break fixation
//												} else {
//													SachEventUtil.fireTrialBREAKEvent(timeUtil.currentTimeMicros(), trialEventListeners, currentContext,i,false);
//													return result;
//												}
//											}
//										} else {
											if (stateObject.getTimeoutPenaltyDelay() < stateObject.getTimeoutBaseDelay()*20)												
												stateObject.setTimeoutPenaltyDelay(stateObject.getTimeoutPenaltyDelay() + stateObject.getTimeoutBaseDelay());
											
											stateObject.resetStreak();
											SachEventUtil.fireTrialBREAKEvent(timeUtil.currentTimeMicros(), trialEventListeners, currentContext,i,false);
											SachExperimentUtil.waitTimeoutPenaltyDelay(stateObject, threadHelper);
											return result;
//										}
									}
									
//									

									boolean doISI = true;
									
									if (i < countObject - 1) {
										// prepare second object
//										stateObject.setAnimation(XmlUtil.isAnimation((Node)objectNodeList.get(i+1)));
										currentContext.setSlideIndex(i + 1);
										// setTask is being called in prepareNextSlide, which is redundant since we are not getting new tasks.
										// It was designed for classic experiment designs, which can have multiple tasks per trial with one slide per task.
										// This experiment scheme is doing one task per trial with multiple slides defined inside one task.
										// We still need to draw new objects for next slide by calling prepareNextSlide.
										drawingController.prepareNextSlide(currentTask, currentContext);
									}

									//if (!SachExperimentUtil.isLastSlide(currentContext) || !SachExperimentUtil.isTargetTrial(currentContext)) { // if this is not a target trial or not the last slide -shs
									if (doISI) {	
										// do inter slide interval
										result = TrialExperimentUtil.waitInterSlideInterval(stateObject,threadHelper);
										if (result != TrialResult.SLIDE_OK) {
//											if (false) {	// last slide and not target trial; need to hold fixation here -shs
//												// (i == countObject-1) && !SachExperimentUtil.isTargetTrial(currentContext)
//												
//												SachEventUtil.fireTrialFAILEvent(timeUtil.currentTimeMicros(), trialEventListeners, currentContext);
//												SachExperimentUtil.waitTimeoutPenaltyDelay(stateObject, threadHelper);
//											} else {
												if (stateObject.getTimeoutPenaltyDelay() < stateObject.getTimeoutBaseDelay()*20)												
													stateObject.setTimeoutPenaltyDelay(stateObject.getTimeoutPenaltyDelay() + stateObject.getTimeoutBaseDelay());
												
												stateObject.resetStreak();
												SachEventUtil.fireTrialBREAKEvent(timeUtil.currentTimeMicros(), trialEventListeners, currentContext,i,true);
												SachExperimentUtil.waitTimeoutPenaltyDelay(stateObject, threadHelper);
												
//											}
											return result;
										}
									}
								} // end 'for' loop

								
								if (SachExperimentUtil.isLastSlide(currentContext) && !SachExperimentUtil.isTargetTrial(currentContext)) {	// shs
									SachEventUtil.fireTrialPASSEvent(timeUtil.currentTimeMicros(), trialEventListeners, currentContext);
								}

								//stateObject.setInterSlideInterval(interSlideInterval);		// ***commented out: now always using regular values for all slides
								//stateObject.setSlideLength(slideLength);

								// trial finished successfully
								// set task to null so that it won't get repeated.
								if (currentTask != null) {
									taskDoneCache.put(currentTask,globalTimeClient.currentTimeMicros(),false);
									currentTask = null;
									stateObject.setCurrentTask(currentTask);
								}
								
								if (stateObject.getTimeoutPenaltyDelay() > stateObject.getTimeoutBaseDelay()*2)												
									stateObject.setTimeoutPenaltyDelay(stateObject.getTimeoutPenaltyDelay()/2);
								else
									stateObject.setTimeoutPenaltyDelay(0);
																
//								SachExperimentUtil.playSingleNote(60,300);
								stateObject.incrementStreak();
								System.out.println("Streak of correct trials: " + stateObject.getStreak());
								long updatedReward = (long)Math.min((long)stateObject.getMinJuice() + stateObject.getStreak()*20, (stateObject.getMinJuice() * 1.5));
								currentContext.setReward(updatedReward);
								
								return TrialResult.TRIAL_COMPLETE;
							} finally {
								try {
									// Do not repeat task (unless repeatTrialIfEyeBreak=true & EYE_BREAK)
									if (!stateObject.isRepeatTrialIfEyeBreak() || result != TrialResult.EYE_BREAK) {
										stateObject.setCurrentTask(null); // Do not repeat task
									}
									TrialExperimentUtil.cleanupTask(stateObject);
								} catch (Exception e) {
									logger.warn(e.getMessage());
									e.printStackTrace();
								}
							}
						}
					});		// end 'runModeRun task'
					
					return ret;
					
				} finally {
					//System.out.println(ret);	// for debugging
					try {
						// repeat if INITIAL_EYE_IN_FAIL or EYE_IN_HOLD_FAIL, otherwise do not repeat
						if (ret != TrialResult.INITIAL_EYE_IN_FAIL && ret != TrialResult.EYE_IN_HOLD_FAIL && ret != TrialResult.EYE_BREAK) {
							stateObject.setCurrentTask(null); // Do not repeat task
						}
						TrialExperimentUtil.cleanupTrial(stateObject);
					} catch (Exception e) {
						logger.warn(e.getMessage());
						e.printStackTrace();
					}
				}


			}
		});
	}

	public void stop() {
		System.out.println("Stopping SachTrialExperiment ...");
		if (isRunning()) {
			threadHelper.stop();
			threadHelper.join();
		}
	}

	public void setPause(boolean pause) {
		stateObject.setPause(pause);
	}

	public SachExperimentState getStateObject() {
		return stateObject;
	}

	public void setStateObject(SachExperimentState stateObject) {
		this.stateObject = stateObject;
	}

	public EyeMonitor getEyeMonitor() {
		return eyeMonitor;
	}

	public void setEyeMonitor(EyeMonitor eyeMonitor) {
		this.eyeMonitor = eyeMonitor;
	}

	public int getFirstSlideISI() {
		return firstSlideISI;
	}

	public void setFirstSlideISI(int firstSlideISI) {
		this.firstSlideISI = firstSlideISI;
	}

	public int getFirstSlideLength() {
		return firstSlideLength;
	}

	public void setFirstSlideLength(int firstSlideLength) {
		this.firstSlideLength = firstSlideLength;
	}

	public int getBlankTargetScreenDisplayTime() {
		return blankTargetScreenDisplayTime;
	}

	public void setBlankTargetScreenDisplayTime(int blankTargetScreenDisplayTime) {
		this.blankTargetScreenDisplayTime = blankTargetScreenDisplayTime;
	}

	public int getEarlyTargetFixationAllowableTime() {
		return earlyTargetFixationAllowableTime;
	}

	public void setEarlyTargetFixationAllowableTime(
			int earlyTargetFixationAllowableTime) {
		this.earlyTargetFixationAllowableTime = earlyTargetFixationAllowableTime;
	}
}
