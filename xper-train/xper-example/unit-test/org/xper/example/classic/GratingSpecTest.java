package org.xper.example.classic;

import junit.framework.TestCase;

import org.xper.rfplot.drawing.GratingSpec;

public class GratingSpecTest extends TestCase {
	public void testXml () {
		GratingSpec g = GaborSpecGenerator.generate();
		String xml = g.toXml();
		//System.out.println(xml);
		GratingSpec g1 = GratingSpec.fromXml(xml);
		assertEquals(g.getFrequency(), g1.getFrequency(), 0.00001);
	}
}