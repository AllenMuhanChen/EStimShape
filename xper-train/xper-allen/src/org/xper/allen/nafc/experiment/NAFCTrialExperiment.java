package org.xper.allen.nafc.experiment;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.allen.util.AllenDbUtil;
import org.xper.experiment.Experiment;
import org.xper.eye.EyeMonitor;
import org.xper.time.TimeUtil;
import org.xper.util.*;

import jssc.SerialPortException;

import static org.xper.util.TrialExperimentUtil.pauseExperiment;

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
			threadHelper.started();
			System.out.println("NAFCExperiment started.");
			stateObject.getDrawingController().init();
			EventUtil.fireExperimentStartEvent(timeUtil.currentTimeMicros(),
					stateObject.getExperimentEventListeners());

			while (!threadHelper.isDone()) {
				pauseExperiment(stateObject, threadHelper);
				if (threadHelper.isDone()) {
					break;
				}
				// one trial
				try{
					getTrialRunner().runTrial(stateObject, threadHelper);
				} catch (NullPointerException e){
					e.printStackTrace();
					System.out.println("THERE ARE NO MORE TRIALS");
				}
				if (threadHelper.isDone()) {
					break;
				}
				long current = timeUtil.currentTimeMicros();
				ThreadUtil.sleepOrPinUtil(current
								+ stateObject.getInterTrialInterval() * 1000, stateObject,						threadHelper);
			}
		} finally {
			// experiment stop event
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

	public NAFCExperimentState getStateObject() {
		return stateObject;
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
	public EyeMonitor getEyeMonitor() {
		return eyeMonitor;
	}
	public void setEyeMonitor(EyeMonitor eyeMonitor) {
		this.eyeMonitor = eyeMonitor;
	}


	public void setTrialRunner(NAFCTrialRunner trialRunner) {
		this.trialRunner = trialRunner;
	}
}
