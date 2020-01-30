package org.xper.example.classic;

import junit.framework.TestCase;

import org.xper.example.classic.GaborSpecGenerator;
import org.xper.rfplot.GaborSpec;

public class GaborSpecTest extends TestCase {
	public void testXml () {
		GaborSpec g = GaborSpecGenerator.generate();
		String xml = g.toXml();
		//System.out.println(xml);
		GaborSpec g1 = GaborSpec.fromXml(xml);
		assertEquals(g.getFrequency(), g1.getFrequency(), 0.00001);
	}
}
