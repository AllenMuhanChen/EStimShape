package org.xper.allen.experiment.saccade;

import org.xper.allen.specs.GaussSpec;
import org.xper.drawing.Coordinates2D;
import org.xper.experiment.ExperimentTask;

/**
 * Holds information regarding the stimulus that does not go to the drawing controller, but something else within the experimental code. 
 * @author allenchen
 *
 */
public class SaccadeExperimentTask extends ExperimentTask {
	
	public Coordinates2D parseCoords() {
		GaussSpec g = GaussSpec.fromXml(this.getStimSpec());
		Coordinates2D coords = new Coordinates2D(g.getXCenter(),g.getYCenter());
		return coords;
	}
	
	public double getDuration() {
		GaussSpec g = GaussSpec.fromXml(this.getStimSpec());
		return g.getDuration();
	}
}
