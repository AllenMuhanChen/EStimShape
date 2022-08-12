package org.xper.fixcal;

import org.xper.classic.TrialExperimentConsoleRenderer;
import org.xper.classic.TrialExperimentMessageHandler;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.object.FixationPoint;

public class FixCalConsoleRenderer extends TrialExperimentConsoleRenderer {
	@Override
	public void drawCanvas(Context context, String devId) {
		TrialExperimentMessageHandler handler = getMessageHandler();
		if (handler instanceof FixCalMessageHandler) {
			Coordinates2D pos = ((FixCalMessageHandler)handler).getFixationPosition();
			((FixationPoint)getFixation()).setFixationPosition(pos);
		}
		super.drawCanvas(context, devId);
	}
}
