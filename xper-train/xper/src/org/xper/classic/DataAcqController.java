package org.xper.classic;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.acq.AcqDeviceController;
import org.xper.classic.vo.TrialContext;
import org.xper.experiment.listener.ExperimentEventListener;

public class DataAcqController implements TrialEventListener,
		ExperimentEventListener {
	static Logger logger = Logger.getLogger(DataAcqController.class);
	
	@Dependency
	AcqDeviceController acqDeviceController;
	@Dependency
	boolean offline = false;

	public void eyeInBreak(long timestamp, TrialContext context) {
	}

	public void eyeInHoldFail(long timestamp, TrialContext context) {
	}

	public void fixationPointOn(long timestamp, TrialContext context) {
	}

	public void fixationSucceed(long timestamp, TrialContext context) {
	}

	public void initialEyeInFail(long timestamp, TrialContext context) {
	}

	public void initialEyeInSucceed(long timestamp, TrialContext context) {
	}

	public void trialComplete(long timestamp, TrialContext context) {
	}
	
	public void trialInit(long timestamp, TrialContext context) {
		logger.info("Start acq server: " + (offline?"offline":"online"));
		if (!offline) {
			acqDeviceController.start();
		}
	}

	public void trialStart(long timestamp, TrialContext context) {
	}

	public void trialStop(long timestamp, TrialContext context) {
		logger.info("Stop acq server: " + (offline?"offline":"online"));
		if (!offline) {
			acqDeviceController.stop();
		}
	}

	public AcqDeviceController getAcqDeviceController() {
		return acqDeviceController;
	}

	public void setAcqDeviceController(AcqDeviceController acqDeviceController) {
		this.acqDeviceController = acqDeviceController;
	}

	public void experimentStart(long timestamp) {
		logger.info("Connect acq server: " + (offline?"offline":"online"));
		if (!offline) {
			acqDeviceController.connect();
		}
	}

	public void experimentStop(long timestamp) {
		logger.info("Disconnect acq server: " + (offline?"offline":"online"));
		if (!offline) {
			acqDeviceController.disconnect();
		}
	}

	public boolean isOffline() {
		return offline;
	}

	public void setOffline(boolean offline) {
		this.offline = offline;
	}

}
