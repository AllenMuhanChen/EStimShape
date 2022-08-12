package org.xper.time;

import org.xper.util.OsUtil;

/**
 * Requires micro second precision clock. 
 * This local time util has to be thread safe, since it might be used in different thread (e.g. EyeTargetSelectorConcurrentDriver).
 * 
 * @author Zhihong Wang
 *
 */
public class DefaultTimeUtil implements TimeUtil {
	public long currentTimeMicros() {
		long next = OsUtil.getTimeOfDay();
		return next;
	}
}
