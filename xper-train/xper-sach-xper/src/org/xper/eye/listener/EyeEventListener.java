package org.xper.eye.listener;

import org.xper.eye.vo.EyePosition;



public interface EyeEventListener {
	/**
	 * 
	 * @param eyePos for each EyeDevice
	 * @param timestamp when eye starts to become in or out. in microseconds.
	 */
	public void eyeIn(EyePosition eyePos, long timestamp);
	public void eyeOut(EyePosition eyePos, long timestamp);
}