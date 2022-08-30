package org.xper.util;

import junit.framework.TestCase;

public class BitOpTest extends TestCase {
	public void testMask () {
		long mask = 0;
		mask |= 1 << 0;
		mask |= 1 << 2;
		assertEquals(5, mask);
	}
	
	public void teseSize () {
		assertEquals(4 * 8, Float.SIZE);
	}
}
