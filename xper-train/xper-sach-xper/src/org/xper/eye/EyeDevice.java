package org.xper.eye;

import org.xper.acq.device.AcqSamplingDevice;
import org.xper.drawing.Coordinates2D;

public interface EyeDevice {

	/**
	 * Read the data for this EyeDevice from AcqSamplingDevice.
	 * 
	 * @param dev
	 */
	public void readEyeSignal(AcqSamplingDevice dev);
	
	public Coordinates2D getEyePosition();
	
	public boolean isEyeZeroUpdateEnabled();
	public void setEyeZeroUpdateEnabled(boolean eyeZeroUpdateEnabled);

	/**
	 * Use this method to test if eyes are in some specific eye window.
	 * 
	 * @param eyeWinCenter
	 * @param eyeWinSize
	 * @return
	 */
	public boolean isIn(Coordinates2D eyeWinCenter, double eyeWinSize);
}
