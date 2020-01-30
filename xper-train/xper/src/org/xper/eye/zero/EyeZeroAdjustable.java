package org.xper.eye.zero;

/**
 * Eye device that has adjustable eye zero need to implement this interface.
 * 
 * @author Zhihong Wang
 *
 */
public interface EyeZeroAdjustable {	
	public void startEyeZeroSignalCollection();
	public void stopEyeZeroSignalCollection();
	public void calculateNewEyeZero ();
}
