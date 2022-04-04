package org.xper.allen.nafc.eye;

import org.xper.classic.vo.TrialContext;
import org.xper.eye.win.EyeWindowAdjustable;
import org.xper.eye.zero.EyeZeroAdjustable;

/**
 * With a free head, eye signals are going to drift more due to head movements.
 * To address this, we modify the behavior of eye-zero updating to update during any failure of fixation
 * 
 * To accompany this, we also need to increase the threshold for eye-zero updates in SystemVars
 * @author r2_allen
 *
 */
public class FreeHeadNAFCEyeMonitorController extends NAFCEyeMonitorController {
	
	public void fixationPointOn(long timestamp, TrialContext context) {
		if(!getEyeSampler().isRunning())
			getEyeSampler().start();
		for (EyeZeroAdjustable dev : getEyeDeviceWithAdjustableZero()) {
			dev.startEyeZeroSignalCollection();
		}
	}
	
	/**
	 * Adjust zeros if this happens, because this is precisely one scenario in which we want 
	 * to adjust in a head-free scenario. Animal tries to fixate, but is slightly off, we can 
	 * then update the eye-zero. 
	 */
	public void eyeInHoldFail(long timestamp, TrialContext context) {
		updateEyeWindow();
		updateEyeZero();
		stopEyeZeroSignalCollection();
	}

	/**
	 * NAFC doesn't use this, but TrialExperimentUtil does. 
	 */
	public void eyeInBreak(long timestamp, TrialContext context) {
		stopEyeZeroSignalCollection();
	}
	
	public void initialEyeInFail(long timestamp, TrialContext context) {
		updateEyeWindow();
		updateEyeZero();
		stopEyeZeroSignalCollection();
	}
	
	protected void updateEyeWindow() {
		for (EyeWindowAdjustable adj : getEyeWindowAdjustable()) {
			adj.updateEyeWindow();
		}
	}
	
	protected void updateEyeZero() {
		for (EyeZeroAdjustable dev : getEyeDeviceWithAdjustableZero()) {
			dev.calculateNewEyeZero();
		}
		System.out.println("AC00938193: Updated Eye Zero!");
	}
}
