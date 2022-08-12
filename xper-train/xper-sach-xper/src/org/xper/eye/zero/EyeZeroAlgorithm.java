package org.xper.eye.zero;

import org.xper.drawing.Coordinates2D;



public interface EyeZeroAlgorithm {

	public abstract Coordinates2D getNewEyeZero();

	public abstract void startEyeZeroSignalCollection();

	public abstract void stopEyeZeroSignalCollection();

	public abstract void collectEyeZeroSignal(Coordinates2D voltage);

	public abstract double getEyeZeroUpdateEyeWinThreshold();
	
	public abstract Coordinates2D getEyeZeroUpdateEyeWinCenter();

}