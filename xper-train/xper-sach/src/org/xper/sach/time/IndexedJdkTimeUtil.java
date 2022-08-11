package org.xper.sach.time;

import org.xper.exception.OverflowException;
import org.xper.time.TimeUtil;


/**
 * Thread safe. To ensure consistency of timestamps on the same machine, deploy as singleton.
 * This class is used only when microsecond precision of timestamp is required.
 * 
 * @author Zhihong Wang
 *
 */
public class IndexedJdkTimeUtil implements TimeUtil {
	long prev;
	int index;
	
	synchronized public long currentTimeMicros() {
		long cur = System.currentTimeMillis()*1000;
		if (cur == prev) {
			++index;
			if (index >= 1000) {
				throw new OverflowException ("JavaTimeUtil overflow: too many time requests within one millisecond.");
			}
			return (cur + index);
		} else {
			index = 0;
			prev = cur;
			return cur;
		}
	}
}
