package org.xper.util;

import java.util.Set;

import org.apache.log4j.Logger;

public class OsUtil {
	static Logger logger = Logger.getLogger(OsUtil.class);
	/**
	 * CPU sets to be bound to. Starting from 0.
	 * 
	 * @param cpuSet
	 */
	public static void setAffinity(Set<Integer> cpuSet) {
		if (cpuSet.size() > 0) {
			long mask = 0;
			for (Integer i : cpuSet) {
				mask |= 1 << i;
			}
			setAffinity(mask);
			long result = getAffinity();
			if (result != mask) {
				logger.warn("Set affinity error. expected mask: "
						+ mask + " actual mask: " + result);
			}
		} else {
			logger.warn("Empty CPU set.");
		}
	}

	native static void setAffinity(long mask);

	native static long getAffinity();
	
	/**
	 * @return time in micro-seconds.
	 */
	public native static long getTimeOfDay();
}
