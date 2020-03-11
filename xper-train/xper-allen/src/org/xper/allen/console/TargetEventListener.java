package org.xper.allen.console;

import org.xper.classic.vo.TrialContext;

public interface TargetEventListener {
	/**
	 * @param timestamp (microseconds)
	 * @param context
	 */
	public void targetOn(long timestamp, TrialContext context);
	/**
	 * @param timestamp (microseconds)
	 * @param context
	 */
	public void targetOff(long timestamp, TrialContext context);
}
