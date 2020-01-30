package org.xper.fixcal;

import org.xper.classic.TrialEventListener;
import org.xper.classic.vo.TrialContext;
import org.xper.drawing.Coordinates2D;

public interface FixCalEventListener extends TrialEventListener {
	public void calibrationPointSetup (long timestamp, Coordinates2D pos, TrialContext context);
}
