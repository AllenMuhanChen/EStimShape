package org.xper.allen.console;

import org.xper.Dependency;
import org.xper.classic.TrialExperimentConsoleRenderer;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.GLUtil;

public class SaccadeExperimentConsoleRenderer extends TrialExperimentConsoleRenderer{
	@Dependency 
	SaccadeExperimentMessageHandler messageHandler;
	
	double targetIndicatorSize = 2.5;
	
	public void drawCanvas(Context context, String devId) {
		super.drawCanvas(context, devId);
		if(messageHandler.isInTrial()) {
			drawTarget();
		}
		
	}
	
	void drawTarget() {
		if(messageHandler.isTargetOn()) {
			Coordinates2D targetLocation = messageHandler.getTargetPosition();
			double targetEyeWindowSize = messageHandler.getTargetEyeWindowSize();
			GLUtil.drawCircle(circle, targetEyeWindowSize, false, targetLocation.getX(), targetLocation.getY(), 0);
			GLUtil.drawSquare(square, targetIndicatorSize, true, targetLocation.getX(), targetLocation.getY(), 0);
		}
	}
}