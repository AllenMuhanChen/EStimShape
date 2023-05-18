package org.xper.allen.nafc.experiment;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.allen.util.AllenDbUtil;
import org.xper.classic.vo.TrialExperimentState;
import org.xper.experiment.Experiment;
import org.xper.eye.EyeMonitor;
import org.xper.time.TimeUtil;
import org.xper.util.*;

import jssc.SerialPortException;



public class NAFCTrialExperiment implements Experiment {
	static Logger logger = Logger.getLogger(NAFCTrialExperiment.class);

	ThreadHelper threadHelper = new ThreadHelper("NAFCTrialExperiment", this);
	@Dependency
	EyeMonitor eyeMonitor;
	@Dependency
	NAFCExperimentState stateObject;
	@Dependency
	AllenDbUtil dbUtil;
	@Dependency
	NAFCTrialRunner trialRunner;

	public boolean isRunning() {
		return threadHelper.isRunning();
	}

	public void start() {
		threadHelper.start();
	}

	public void run() {
		TimeUtil timeUtil = stateObject.getLocalTimeUtil();
		try {
			startExperiment(timeUtil);

			while (!threadHelper.isDone()) {
				//pause experiment
				pauseUntilRunReceived();
				if (stopReceived()) break;
				runTrial();
				if (stopReceived()) break;
				interTrialInterval(timeUtil);
			}
		} finally {
			stopExperiment(timeUtil);
		}
	}

	protected void startExperiment(TimeUtil timeUtil) {
		threadHelper.started();
		System.out.println("NAFCTrialExperiment started.");
		stateObject.getDrawingController().init();
		EventUtil.fireExperimentStartEvent(timeUtil.currentTimeMicros(),
				stateObject.getExperimentEventListeners());
	}

	protected void runTrial() {
		try{
			getTrialRunner().runTrial(stateObject, threadHelper);
		} catch (NullPointerException e){
			e.printStackTrace();
			System.out.println("THERE ARE NO MORE TRIALS");
		}
	}

	private void stopExperiment(TimeUtil timeUtil) {
		try {
			System.out.println("NAFCExperiment stopped.");
			EventUtil.fireExperimentStopEvent(timeUtil.currentTimeMicros(),
					stateObject.getExperimentEventListeners());
			stateObject.getDrawingController().destroy();

			threadHelper.stopped();
		} catch (Exception e) {
			//logger.warn(e.getMessage());
			e.printStackTrace();
		}
	}

	public void pauseUntilRunReceived() {
		TimeUtil timeUtil = stateObject.getLocalTimeUtil();
		while (stateObject.isPause()) {
			ThreadUtil.sleepOrPinUtil(timeUtil.currentTimeMicros()
							+ TrialExperimentState.EXPERIMENT_PAUSE_SLEEP_INTERVAL * 1000, stateObject,
					threadHelper);
			if (threadHelper.isDone()) {
				return;
			}
		}
	}

	private void interTrialInterval(TimeUtil timeUtil) {
		long current = timeUtil.currentTimeMicros();
		ThreadUtil.sleepOrPinUtil(current
						+ stateObject.getInterTrialInterval() * 1000L, stateObject, threadHelper);
	}

	private boolean stopReceived() {
		if (threadHelper.isDone()) {
			return true;
		}
		return false;
	}

	public void stop() {
		System.out.println("Stopping NAFCTrialExperiment ...");
		if (isRunning()) {
			threadHelper.stop();
			threadHelper.join();
		}
	}

	public NAFCTrialRunner getTrialRunner() {
		return trialRunner;
	}

	public void setStateObject(NAFCExperimentState stateObject) {
		this.stateObject = stateObject;
	}

	public void setPause(boolean pause) {
		stateObject.setPause(pause);
	}


	public AllenDbUtil getDbUtil() {
		return dbUtil;
	}

	public void setDbUtil(AllenDbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}

	public void setEyeMonitor(EyeMonitor eyeMonitor) {
		this.eyeMonitor = eyeMonitor;
	}

	public void setTrialRunner(NAFCTrialRunner trialRunner) {
		this.trialRunner = trialRunner;
	}

}