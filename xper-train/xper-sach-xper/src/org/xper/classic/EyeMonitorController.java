package org.xper.classic;

import java.util.List;

import org.xper.Dependency;
import org.xper.classic.vo.TrialContext;
import org.xper.eye.EyeSampler;
import org.xper.eye.win.EyeWindowAdjustable;
import org.xper.eye.zero.EyeZeroAdjustable;

/**
 * Controls eye monitor start, stop and update of zero and eye window when
 * necessary
 * 
 * @author Zhihong Wang
 * 
 */
public class EyeMonitorController implements TrialEventListener {
	@Dependency
	EyeSampler eyeSampler;
	@Dependency
	List<EyeWindowAdjustable> eyeWindowAdjustable;
	@Dependency
	List<EyeZeroAdjustable> eyeDeviceWithAdjustableZero;

	public EyeSampler getEyeSampler() {
		return eyeSampler;
	}

	public void setEyeSampler(EyeSampler eyeSampler) {
		this.eyeSampler = eyeSampler;
	}

	public void fixationPointOn(long timestamp, TrialContext context) {
		eyeSampler.start();
		for (EyeZeroAdjustable dev : eyeDeviceWithAdjustableZero) {
			dev.startEyeZeroSignalCollection();
		}
	}
	
	void stopEyeZeroSignalCollection() {
		for (EyeZeroAdjustable dev : eyeDeviceWithAdjustableZero) {
			dev.stopEyeZeroSignalCollection();
		}
	}

	public void trialStop(long timestamp, TrialContext context) {
		if (eyeSampler.isRunning()) {
			eyeSampler.stop();
		}
		
		for (EyeZeroAdjustable dev : eyeDeviceWithAdjustableZero) {
			dev.calculateNewEyeZero();
		}
	}

	public List<EyeZeroAdjustable> getEyeDeviceWithAdjustableZero() {
		return eyeDeviceWithAdjustableZero;
	}

	public void setEyeDeviceWithAdjustableZero(
			List<EyeZeroAdjustable> eyeDeviceWithAdjustableZero) {
		this.eyeDeviceWithAdjustableZero = eyeDeviceWithAdjustableZero;
	}

	public void eyeInHoldFail(long timestamp, TrialContext context) {
	}

	public void fixationSucceed(long timestamp, TrialContext context) {
	}

	public void initialEyeInFail(long timestamp, TrialContext context) {
	}

	public void initialEyeInSucceed(long timestamp, TrialContext context) {
	}

	public void trialComplete(long timestamp, TrialContext context) {
		for (EyeWindowAdjustable adj : eyeWindowAdjustable) {
			adj.updateEyeWindow();
		}
		stopEyeZeroSignalCollection();
	}
	
	public void trialInit(long timestamp, TrialContext context) {
	}

	public void trialStart(long timestamp, TrialContext context) {
	}

	public void eyeInBreak(long timestamp, TrialContext context) {
		stopEyeZeroSignalCollection();
	}

	public List<EyeWindowAdjustable> getEyeWindowAdjustable() {
		return eyeWindowAdjustable;
	}

	public void setEyeWindowAdjustable(List<EyeWindowAdjustable> eyeWindowAdjustable) {
		this.eyeWindowAdjustable = eyeWindowAdjustable;
	}
}
