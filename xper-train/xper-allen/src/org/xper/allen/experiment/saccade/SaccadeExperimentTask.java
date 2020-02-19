package org.xper.allen.experiment.saccade;

import org.xper.allen.specs.GaussSpec;
import org.xper.drawing.Coordinates2D;
import org.xper.experiment.ExperimentTask;

public class SaccadeExperimentTask extends ExperimentTask {
	
	public Coordinates2D parseCoords() {
		GaussSpec g = GaussSpec.fromXml(this.getStimSpec());
		Coordinates2D coords = new Coordinates2D(g.getXCenter(),g.getYCenter());
		return coords;
	}
}
