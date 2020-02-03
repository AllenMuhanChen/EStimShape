package org.xper.allen.experiment;

import org.xper.experiment.StimSpecGenerator;
import org.xper.rfplot.GaborSpec;

public class GaussianSpecGenerator implements StimSpecGenerator {
	static int XCenter = 0;
	static int YCenter = 0;
	static int Size = 100;
	static int Orientation = (int) (Math.random() * Math.PI);
	static int Frequency = 0;
	static int Phase = (int) Math.PI;
	static boolean Animation = true;
	
	//Default Constructor
	public GaussianSpecGenerator() {
		super();
	}
	
	//Location & Size Constructor
	public GaussianSpecGenerator(int XCenter, int YCenter, int Size) {
		GaussianSpecGenerator.XCenter = XCenter;
		GaussianSpecGenerator.YCenter = YCenter;
		GaussianSpecGenerator.Size = Size;
	}


	public static GaborSpec generate() {
		GaborSpec g = new GaborSpec();
		g.setXCenter(XCenter);
		g.setYCenter(YCenter);
		g.setSize(Size);
		g.setOrientation(Orientation);
		g.setFrequency(Frequency);
		g.setPhase(Phase);
		g.setAnimation(Animation);
		return g;
	}
	

	public String generateStimSpec() {
		return GaussianSpecGenerator.generate().toXml();
	}
}
