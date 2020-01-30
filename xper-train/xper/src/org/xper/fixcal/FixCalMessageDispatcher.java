package org.xper.fixcal;

import org.xper.classic.TrialExperimentMessageDispatcher;
import org.xper.classic.vo.TrialContext;
import org.xper.drawing.Coordinates2D;

public class FixCalMessageDispatcher extends TrialExperimentMessageDispatcher
		implements FixCalEventListener {

	public void calibrationPointSetup(long timestamp, Coordinates2D pos,
			TrialContext context) {
		enqueue(timestamp, "CalibrationPointSetup", CalibrationPointSetupMessage
				.toXml(new CalibrationPointSetupMessage(pos)));
	}

}
