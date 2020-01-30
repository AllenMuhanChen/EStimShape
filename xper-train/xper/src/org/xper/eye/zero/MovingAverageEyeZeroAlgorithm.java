package org.xper.eye.zero;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.drawing.Coordinates2D;

public class MovingAverageEyeZeroAlgorithm implements EyeZeroAlgorithm {
	static Logger logger = Logger
			.getLogger(MovingAverageEyeZeroAlgorithm.class);

	/**
	 * Only update eye zero when it is in this eye window threshold.
	 */
	@Dependency
	double eyeZeroUpdateEyeWinThreshold;
	@Dependency
	Coordinates2D eyeZeroUpdateEyeWinCenter;

	/**
	 * Only update eye zero when more samples are obtained than this number.
	 */
	@Dependency
	int eyeZeroUpdateMinSample;

	Coordinates2D eyeZeroSampleSum = new Coordinates2D();
	int eyeZeroSampleCount;
	boolean collectingEyeZeroSignal = false;
	Coordinates2D[] eyeZero;
	int eyeZeroIndex = 0;

	public MovingAverageEyeZeroAlgorithm(int span) {
		eyeZero = new Coordinates2D[span];
		for (int i = 0; i < span; i++) {
			eyeZero[i] = new Coordinates2D();
		}
	}

	public Coordinates2D getNewEyeZero() {
		if (eyeZeroIndex == 0)
			return null;

		Coordinates2D average = new Coordinates2D();
		int n = eyeZeroIndex > eyeZero.length ? eyeZero.length : eyeZeroIndex;

		for (int i = 0; i < n; i++) {
			average.setX(average.getX() + eyeZero[i].getX());
			average.setY(average.getY() + eyeZero[i].getY());
		}

		average.setX(average.getX() / n);
		average.setY(average.getY() / n);

		if (logger.isDebugEnabled()) {
			logger.debug("n: " + n + " average: " + average.getX() + " "
					+ average.getY());
		}
		return average;
	}

	public void startEyeZeroSignalCollection() {
		eyeZeroSampleCount = 0;
		eyeZeroSampleSum.setX(0);
		eyeZeroSampleSum.setY(0);
		collectingEyeZeroSignal = true;
	}

	public void stopEyeZeroSignalCollection() {
		collectingEyeZeroSignal = false;
		if (eyeZeroSampleCount >= eyeZeroUpdateMinSample) {
			int i = eyeZeroIndex % eyeZero.length;
			eyeZero[i].setX(eyeZeroSampleSum.getX() / eyeZeroSampleCount);
			eyeZero[i].setY(eyeZeroSampleSum.getY() / eyeZeroSampleCount);

			if (logger.isDebugEnabled()) {
				logger.debug("i: " + i + " index: " + eyeZeroIndex + " zero: "
						+ eyeZero[i].getX() + " " + eyeZero[i].getY());
			}
			eyeZeroIndex++;
		}
	}

	public void collectEyeZeroSignal(Coordinates2D voltage) {
		if (collectingEyeZeroSignal) {
			eyeZeroSampleCount++;
			eyeZeroSampleSum.setX(eyeZeroSampleSum.getX() + voltage.getX());
			eyeZeroSampleSum.setY(eyeZeroSampleSum.getY() + voltage.getY());
		}
		/*if (logger.isDebugEnabled()) {
			logger
					.debug("volt: " + voltage.getX() + " " + voltage.getY()
							+ " sum: " + eyeZeroSampleSum.getX() + " "
							+ eyeZeroSampleSum.getY() + " count: "
							+ eyeZeroSampleCount);
		}*/
	}

	public double getEyeZeroUpdateEyeWinThreshold() {
		return eyeZeroUpdateEyeWinThreshold;
	}

	public void setEyeZeroUpdateEyeWinThreshold(
			double eyeZeroUpdateEyeWinThreshold) {
		this.eyeZeroUpdateEyeWinThreshold = eyeZeroUpdateEyeWinThreshold;
	}

	public int getEyeZeroUpdateMinSample() {
		return eyeZeroUpdateMinSample;
	}

	public void setEyeZeroUpdateMinSample(int eyeZeroUpdateMinSample) {
		this.eyeZeroUpdateMinSample = eyeZeroUpdateMinSample;
	}

	public Coordinates2D getEyeZeroUpdateEyeWinCenter() {
		return this.eyeZeroUpdateEyeWinCenter;
	}

	public void setEyeZeroUpdateEyeWinCenter(Coordinates2D eyeZeroUpdateEyeWinCenter) {
		this.eyeZeroUpdateEyeWinCenter = eyeZeroUpdateEyeWinCenter;
	}

}
