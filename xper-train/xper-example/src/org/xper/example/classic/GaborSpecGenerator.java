package org.xper.example.classic;

import org.xper.experiment.StimSpecGenerator;
import org.xper.rfplot.drawing.GratingSpec;

public class GaborSpecGenerator implements StimSpecGenerator {
	public static GratingSpec generate () {
		GratingSpec g = new GratingSpec();
		g.setXCenter(0);
		g.setYCenter(0);
		g.setSize(100);
		g.setOrientation(Math.random() * Math.PI);
		g.setFrequency(0.02);
		g.setPhase(Math.PI);
		g.setAnimation(true);
		return g;
	}

	public String generateStimSpec() {
		return GaborSpecGenerator.generate().toXml();
	}
}