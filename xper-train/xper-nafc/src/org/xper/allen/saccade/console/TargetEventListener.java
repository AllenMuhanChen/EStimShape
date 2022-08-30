package org.xper.allen.saccade.console;

import org.xper.classic.TrialEventListener;
import org.xper.classic.vo.TrialContext;

public interface TargetEventListener{
	/**
	 * @param timestamp (microseconds)
	 * @param context
	 */
	public void targetOn(long timestamp, TrialContext context);
	/**
	 * @param timestamp (microseconds)
	 * @param context
	 */
	public void targetOff(long timestamp);
	
	public void targetSelectionEyeFail(long timestamp);
	
	public void targetSelectionEyeBreak(long timestamp);
	public void targetSelectionDone(long timestamp);
	
}
