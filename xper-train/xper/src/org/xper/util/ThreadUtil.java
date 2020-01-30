package org.xper.util;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.TimeUnit;

import org.jdesktop.swingworker.SwingWorker;
import org.xper.classic.vo.TrialExperimentState;
import org.xper.time.TimeUtil;

public class ThreadUtil {
	
	public static void backgroundRun (final Runnable job, final Runnable doneJob) {
		SwingWorker<Void, Void> worker = new SwingWorker<Void, Void>() {
			@Override
			public Void doInBackground() throws Exception {
				job.run();
				return null;
			}
			@Override
		    public void done() {
				if (doneJob != null) {
					doneJob.run();
				}
			}
		};
		worker.execute();
	}
	
	public static void shutdownExecutorService (ExecutorService service) {
		service.shutdown();
		boolean done = false;
		while (!done) {
			try {
				done = service.awaitTermination(10, TimeUnit.MILLISECONDS);
			} catch (InterruptedException e) {
				e.printStackTrace();
			}
		}
	}
	/**
	 * 
	 * @param target in microseconds
	 * @param timeUtil
	 */
	public static void sleepUtil(long target, TimeUtil timeUtil) {
		long current = timeUtil.currentTimeMicros();
		while (current < target) {
			try {
				Thread.sleep((target - current) / 1000);
			} catch (InterruptedException e) {
			}
			current = timeUtil.currentTimeMicros();
		}
	}
	
	/**
	 * 
	 * @param target in microseconds
	 * @param experiment
	 * @param threadHelper
	 */
	public static void sleepOrPinUtil(long target,
			TrialExperimentState experiment, ThreadHelper threadHelper) {
		if (experiment.isSleepWhileWait()) {
			sleepUtil(target, experiment, threadHelper);
		} else {
			pinUtil(target, experiment, threadHelper);
		}
	}

	/**
	 * 
	 * @param target in microseconds
	 * @param experiment
	 * @param threadHelper
	 */
	public static void sleepUtil(long target, TrialExperimentState experiment,
			ThreadHelper threadHelper) {
		TimeUtil timeUtil = experiment.getLocalTimeUtil();
		long current = timeUtil.currentTimeMicros();
		while (current < target) {
			try {
				Thread.sleep((target - current)/1000 >= TrialExperimentState.SLEEP_INTERVAL ? TrialExperimentState.SLEEP_INTERVAL
								: (target - current)/1000);
			} catch (InterruptedException e) {
			}
			if (threadHelper.isDone()) {
				return;
			}
			current = timeUtil.currentTimeMicros();
		}
	}

	/**
	 * 
	 * @param target in microseconds
	 * @param experiment
	 * @param threadHelper
	 */
	public static void pinUtil(long target, TrialExperimentState experiment,
			ThreadHelper threadHelper) {
		TimeUtil timeUtil = experiment.getLocalTimeUtil();
		while (timeUtil.currentTimeMicros() < target) {
			if (threadHelper.isDone()) {
				return;
			}
		}
	}
	
	/**
	 * 
	 * @param time in milliseconds
	 */
	public static void sleep (long time) {
		try {
			Thread.sleep(time);
		} catch (InterruptedException e) {
		}
	}
}
