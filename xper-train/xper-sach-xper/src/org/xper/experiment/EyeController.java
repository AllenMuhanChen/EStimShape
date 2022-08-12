package org.xper.experiment;

public interface EyeController {

	/**
	 * 
	 * @param target
	 *            in microseconds.
	 */
	public boolean waitInitialEyeIn(long target);

	public boolean waitEyeInAndHold(long target);

	public boolean isEyeIn();

}
