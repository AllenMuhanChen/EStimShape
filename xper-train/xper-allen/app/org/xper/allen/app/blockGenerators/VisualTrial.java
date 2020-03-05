package org.xper.allen.app.blockGenerators;

import org.xper.allen.app.blockGenerators.trials.Trial;
import org.xper.allen.app.blockGenerators.trials.visualTrial;
import org.xper.allen.specs.GaussSpec;

import com.thoughtworks.xstream.XStream;

public class VisualTrial {
	GaussSpec gaussSpec;
	double targetEyeWinsize;
	transient XStream s = new XStream();
	
	public VisualTrial(GaussSpec gaussSpec, double targetEyeWinsize) {
		super();
		this.gaussSpec = gaussSpec;
		this.targetEyeWinsize = targetEyeWinsize;
		s.alias("VisualTrial", VisualTrial.class);
		s.setMode(XStream.NO_REFERENCES);
	}
	
	public String toXml() {
		return s.toXML(this);
	}
}
