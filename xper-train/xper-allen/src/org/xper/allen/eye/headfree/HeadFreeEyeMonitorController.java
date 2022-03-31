package org.xper.allen.eye.headfree;

import java.util.List;

import org.xper.classic.EyeMonitorController;
import org.xper.classic.vo.TrialContext;
import org.xper.eye.win.EyeWindowAdjustable;
import org.xper.eye.zero.EyeZeroAdjustable;

public class HeadFreeEyeMonitorController extends EyeMonitorController{
	private
	List<HeadFreeEyeZeroAdjustable> eyeDeviceWithHeadFreeAdjustableZero;
	
	protected void startInnerEyeZeroSignalCollection() {
		for (HeadFreeEyeZeroAdjustable dev : getEyeDeviceWithHeadFreeAdjustableZero()) {
			dev.startEyeZeroInnerSignalCollection();
		}
	}
	
	protected void startEyeZeroSignalCollection() {
		for (HeadFreeEyeZeroAdjustable dev : getEyeDeviceWithHeadFreeAdjustableZero()) {
			dev.startEyeZeroSignalCollection();
		}
	}
	
	protected void stopEyeZeroSignalCollection() {
		for (HeadFreeEyeZeroAdjustable dev : getEyeDeviceWithHeadFreeAdjustableZero()) {
			dev.stopEyeZeroSignalCollection();
			dev.stopEyeZeroInnerSignalCollection();
		}
	}
	
	public void fixationPointOn(long timestamp, TrialContext context) {
		getEyeSampler().start();
		startEyeZeroSignalCollection();
	}
	public void initialEyeInSucceed (long timestamp, TrialContext context) {
		startInnerEyeZeroSignalCollection();
	}
	
	public void eyeInHoldFail(long timestamp, TrialContext context) {
		stopEyeZeroSignalCollection();
		for (EyeZeroAdjustable dev : getEyeDeviceWithHeadFreeAdjustableZero()) {
			dev.calculateNewEyeZero();
		}
	}
	
	public void fixationSucceed(long timestamp, TrialContext context) {
		for (EyeWindowAdjustable adj : getEyeWindowAdjustable()) {
			adj.updateEyeWindow();
		}
		for (EyeZeroAdjustable dev : getEyeDeviceWithHeadFreeAdjustableZero()) {
			dev.calculateNewEyeZero();
		}
		stopEyeZeroSignalCollection();
	}
	
	/**
	 * We no longer want to calculateNewEyeZero() here. Instead we do it after fixation success. 
	 */
	public void trialStop(long timestamp, TrialContext context) {
		if (getEyeSampler().isRunning()) {
			getEyeSampler().stop();
		}
	}
	
	
	public void trialComplete(long timestamp, TrialContext context) {
	}

	public List<HeadFreeEyeZeroAdjustable> getEyeDeviceWithHeadFreeAdjustableZero() {
		return eyeDeviceWithHeadFreeAdjustableZero;
	}

	public void setEyeDeviceWithHeadFreeAdjustableZero(
			List<HeadFreeEyeZeroAdjustable> eyeDeviceWithHeadFreeAdjustableZero) {
		this.eyeDeviceWithHeadFreeAdjustableZero = eyeDeviceWithHeadFreeAdjustableZero;
	}

}
