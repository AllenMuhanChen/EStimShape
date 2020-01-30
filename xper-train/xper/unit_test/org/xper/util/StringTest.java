package org.xper.util;

import java.io.File;

import junit.framework.TestCase;

public class StringTest extends TestCase {
	public void testReplaceAll() {
		String src = "lib/test.so";
		String dest = src.replace('/', File.separatorChar);
		assertEquals("lib" + File.separatorChar + "test.so", dest);
	}
}
