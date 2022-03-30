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
	private
	int eyeZeroUpdateMinSample;

	private Coordinates2D eyeZeroSampleSum = new Coordinates2D();
	private int eyeZeroSampleCount;
	private boolean collectingEyeZeroSignal = false;
	private Coordinates2D[] eyeZero;
	private int eyeZeroIndex = 0;

	public MovingAverageEyeZeroAlgorithm(int span) {
		setEyeZero(new Coordinates2D[span]);
		for (int i = 0; i < span; i++) {
			getEyeZero()[i] = new Coordinates2D();
		}
	}

	public Coordinates2D getNewEyeZero() {
		if (getEyeZeroIndex() == 0)
			return null;

		Coordinates2D average = new Coordinates2D();
		int n = getEyeZeroIndex() > getEyeZero().length ? getEyeZero().length : getEyeZeroIndex();

		for (int i = 0; i < n; i++) {
			average.setX(average.getX() + getEyeZero()[i].getX());
			average.setY(average.getY() + getEyeZero()[i].getY());
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
		setEyeZeroSampleCount(0);
		getEyeZeroSampleSum().setX(0);
		getEyeZeroSampleSum().setY(0);
		setCollectingEyeZeroSignal(true);
	}

	public void stopEyeZeroSignalCollection() {
		setCollectingEyeZeroSignal(false);
		if (getEyeZeroSampleCount() >= getEyeZeroUpdateMinSample()) {
			int i = getEyeZeroIndex() % getEyeZero().length;
			getEyeZero()[i].setX(getEyeZeroSampleSum().getX() / getEyeZeroSampleCount());
			getEyeZero()[i].setY(getEyeZeroSampleSum().getY() / getEyeZeroSampleCount());

			if (logger.isDebugEnabled()) {
				logger.debug("i: " + i + " index: " + getEyeZeroIndex() + " zero: "
						+ getEyeZero()[i].getX() + " " + getEyeZero()[i].getY());
			}
			setEyeZeroIndex(getEyeZeroIndex() + 1);
		}
	}

	public void collectEyeZeroSignal(Coordinates2D voltage) {
		if (isCollectingEyeZeroSignal()) {
			setEyeZeroSampleCount(getEyeZeroSampleCount() + 1);
			getEyeZeroSampleSum().setX(getEyeZeroSampleSum().getX() + voltage.getX());
			getEyeZeroSampleSum().setY(getEyeZeroSampleSum().getY() + voltage.getY());
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

	protected int getEyeZeroSampleCount() {
		return eyeZeroSampleCount;
	}

	protected void setEyeZeroSampleCount(int eyeZeroSampleCount) {
		this.eyeZeroSampleCount = eyeZeroSampleCount;
	}

	public Coordinates2D getEyeZeroSampleSum() {
		return eyeZeroSampleSum;
	}

	public void setEyeZeroSampleSum(Coordinates2D eyeZeroSampleSum) {
		this.eyeZeroSampleSum = eyeZeroSampleSum;
	}

	public boolean isCollectingEyeZeroSignal() {
		return collectingEyeZeroSignal;
	}

	public void setCollectingEyeZeroSignal(boolean collectingEyeZeroSignal) {
		this.collectingEyeZeroSignal = collectingEyeZeroSignal;
	}

	protected int getEyeZeroIndex() {
		return eyeZeroIndex;
	}

	public void setEyeZeroIndex(int eyeZeroIndex) {
		this.eyeZeroIndex = eyeZeroIndex;
	}

	protected Coordinates2D[] getEyeZero() {
		return eyeZero;
	}

	void setEyeZero(Coordinates2D[] eyeZero) {
		this.eyeZero = eyeZero;
	}

}
