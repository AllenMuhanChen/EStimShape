package org.xper.util;

import java.lang.management.ManagementFactory;
import java.lang.management.MemoryMXBean;

import junit.framework.TestCase;

import org.apache.log4j.Logger;

public class ManagementTest extends TestCase {
	static Logger logger = Logger.getLogger(ManagementTest.class);
	
	public void test() {
		MemoryMXBean memory = ManagementFactory.getMemoryMXBean();
		long before = memory.getHeapMemoryUsage().getUsed();
		logger.info("Before gc: " + before);
		memory.gc();
		long after = memory.getHeapMemoryUsage().getUsed();
		logger.info("After gc: " + after);
		assertTrue(after <= before);
	}
}
