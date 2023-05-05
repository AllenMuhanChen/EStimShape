package org.xper.allen.nafc.eye;

import org.xper.allen.nafc.message.ChoiceEventListener;
import org.xper.classic.EyeMonitorController;
import org.xper.classic.vo.TrialContext;
import org.xper.eye.win.EyeWindowAdjustable;
import org.xper.eye.zero.EyeZeroAdjustable;

/**
 * In a NAFC trial, we want to start collecting eye info for eye zero update when fixation point
 * comes on, and stop when fixation succeeds or fails (not end of Trial). We also don't want to collect info from sample, incase
 * animal makes microsaccades as a response. 
 * @author r2_allen
 *
 */
public class NAFCEyeMonitorController extends EyeMonitorController{

	@Override
	public void fixationSucceed(long timestamp, TrialContext context) {
		for (EyeZeroAdjustable dev : getEyeDeviceWithAdjustableZero()) {
			dev.calculateNewEyeZero();
		}
		stopEyeZeroSignalCollection();
	}

	public void trialComplete(long timestamp, TrialContext context) {
		for (EyeWindowAdjustable adj : getEyeWindowAdjustable()) {
			adj.updateEyeWindow();
		}
	}
	
	/**
	 * We no longer want to calculateNewEyeZero() here. Instead we do it after fixation success. 
	 */
	@Override
		public void trialStop(long timestamp, TrialContext context) {
			if (getEyeSampler().isRunning()) {
				getEyeSampler().stop();
			}
		}

	@Override
	public void eyeInHoldFail(long timestamp, TrialContext context) {
		stopEyeZeroSignalCollection();
	}

	@Override
	public void eyeInBreak(long timestamp, TrialContext context) {
		stopEyeZeroSignalCollection();
	}
	


}
