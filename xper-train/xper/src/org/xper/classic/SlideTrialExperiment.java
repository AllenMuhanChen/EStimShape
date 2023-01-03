package org.xper.classic;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.classic.vo.SlideTrialExperimentState;
import org.xper.classic.vo.TrialExperimentState;
import org.xper.experiment.Experiment;
import org.xper.time.TimeUtil;
import org.xper.util.*;

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

	@Dependency
	SlideTrialRunner trialRunner;



	private void stopExperiment() {
		try {
			System.out.println("SlideTrialExperiment stopped.");
			EventUtil.fireExperimentStopEvent(getCurrentTimeMicros(),
					stateObject.getExperimentEventListeners());
			stateObject.getDrawingController().destroy();

			threadHelper.stopped();
		} catch (Exception e) {
			TrialExperimentUtil.logger.warn(e.getMessage());
			e.printStackTrace();
		}
	}

	private long getCurrentTimeMicros() {
		return stateObject.getLocalTimeUtil().currentTimeMicros();
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

	public void startExperiment(TimeUtil timeUtil) {
		threadHelper.started();
		System.out.println("SlideTrialExperiment started.");

		stateObject.getDrawingController().init();
		EventUtil.fireExperimentStartEvent(getCurrentTimeMicros(),
				stateObject.getExperimentEventListeners());
	}

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
				pauseUntilRunReceived();
				if (threadHelper.isDone()) {
					break;
				}
				// one trial
				trialRunner.runTrial(stateObject, threadHelper);
				if (threadHelper.isDone()) {
					break;
				}
				// inter-trial interval
				long current = timeUtil.currentTimeMicros();
				ThreadUtil.sleepOrPinUtil(current
								+ stateObject.getInterTrialInterval() * 1000, stateObject,
						threadHelper);
			}
		} finally {
			stopExperiment();
		}

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

	public SlideTrialRunner getTrialRunner() {
		return trialRunner;
	}

	public void setTrialRunner(SlideTrialRunner trialRunner) {
		this.trialRunner = trialRunner;
	}
}
