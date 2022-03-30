package org.xper.allen.nafc.eye;

import org.xper.drawing.Coordinates2D;
import org.xper.eye.zero.MovingAverageEyeZeroAlgorithm;

public class LaggingMovingAverageEyeZeroAlgorithm extends MovingAverageEyeZeroAlgorithm{

	public LaggingMovingAverageEyeZeroAlgorithm(int span) {
		super(span);
		// TODO Auto-generated constructor stub
	}

	public void stopEyeZeroSignalCollection() {
		setCollectingEyeZeroSignal(false);
		if (getEyeZeroSampleCount() >= getEyeZeroUpdateMinSample()) {
			int i = getEyeZeroIndex() % getEyeZero().length;
			getEyeZero()[i].setX(getEyeZeroSampleSum().getX() / (getEyeZeroSampleCount()-getEyeZeroUpdateMinSample()+1));
			getEyeZero()[i].setY(getEyeZeroSampleSum().getY() / (getEyeZeroSampleCount()-getEyeZeroUpdateMinSample()+1));

			setEyeZeroIndex(getEyeZeroIndex() + 1);
		}
	}
	
	public void collectEyeZeroSignal(Coordinates2D voltage) {
		if (isCollectingEyeZeroSignal()) {
			setEyeZeroSampleCount(getEyeZeroSampleCount() + 1);
			if(getEyeZeroSampleCount()>=getEyeZeroUpdateMinSample()) {
				System.out.println("AC575731890: Using Lagging Moving Average" + getEyeZeroSampleCount());
				getEyeZeroSampleSum().setX(getEyeZeroSampleSum().getX() + voltage.getX());
				getEyeZeroSampleSum().setY(getEyeZeroSampleSum().getY() + voltage.getY());
			}
		}
		/*if (logger.isDebugEnabled()) {
			logger
					.debug("volt: " + voltage.getX() + " " + voltage.getY()
							+ " sum: " + eyeZeroSampleSum.getX() + " "
							+ eyeZeroSampleSum.getY() + " count: "
							+ eyeZeroSampleCount);
		}*/
	}
}
