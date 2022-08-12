package org.xper.classic;

import org.apache.commons.math.stat.descriptive.SummaryStatistics;
import org.apache.log4j.Logger;
import org.xper.classic.vo.TrialContext;
import org.xper.util.StringUtil;

public class ExperimentProfiler implements SlideEventListener,
		TrialEventListener {
	static Logger logger = Logger.getLogger(ExperimentProfiler.class);

	SummaryStatistics slideStat = SummaryStatistics.newInstance();
	long onTimestamp;
	long frameCount = 0;
	double totalTime = 0;

	public void slideOff(int index, long timestamp, int frameCount) {
		double length = timestamp - onTimestamp;
		slideStat.addValue(length/1000.0);
		if (frameCount > 0) {
			this.frameCount += frameCount;
			totalTime += length / 1000000.0;
		}
	}

	public void slideOn(int index, long timestamp) {
		onTimestamp = timestamp;
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
	}

	public void trialStart(long timestamp, TrialContext context) {
	}

	/**
	 * Slide Statistics: 7752 mean: 750.0043859649127 stdev: 0.09493078316425285
	 * max: 754.0 min: 750.0
	 */
	public void trialStop(long timestamp, TrialContext context) {
		logger.info("Slide Statistics: " + slideStat.getN());
		logger.info("mean: " + StringUtil.format(slideStat.getMean(), 1) + " stdev: "
				+ StringUtil.format(slideStat.getStandardDeviation(), 1));
		logger.info("max: " + StringUtil.format(slideStat.getMax(), 1) + " min: "
				+ StringUtil.format(slideStat.getMin(), 1));
		if (frameCount > 0) {
			logger.info(frameCount + " frames in " + StringUtil.format(totalTime, 1) + " seconds = "
					+ StringUtil.format(frameCount / totalTime, 1) + " FPS.");
		}

		slideStat.clear();
		frameCount = 0;
		totalTime = 0;
	}

	public void eyeInBreak(long timestamp, TrialContext context) {
	}

}
