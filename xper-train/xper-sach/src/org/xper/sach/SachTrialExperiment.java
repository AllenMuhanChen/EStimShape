package org.xper.sach;


import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.classic.*;
import org.xper.experiment.Experiment;
import org.xper.eye.EyeMonitor;
//import org.xper.eye.EyeTargetSelector;
import org.xper.sach.vo.SachExperimentState;
import org.xper.util.ThreadHelper;


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
		SlideTrialRunner.run(stateObject, threadHelper);
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
