package org.xper.allen.saccade.console;

import org.xper.Dependency;
import org.xper.classic.TrialExperimentConsoleRenderer;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.GLUtil;

public class SaccadeExperimentConsoleRenderer extends TrialExperimentConsoleRenderer{
	@Dependency 
	SaccadeExperimentMessageHandler messageHandler;
	
	double targetIndicatorSize = 2.5;
	int invert;
	
	public void drawCanvas(Context context, String devId) {
		super.drawCanvas(context, devId);
		if(getMessageHandler().isInTrial()) {
			drawTarget();
		}	
		
	}
	
	void drawTarget() {
		if(messageHandler.isTargetOn()) {
			Coordinates2D targetLocation = messageHandler.getTargetPosition();
			double targetEyeWindowSize = getRenderer().deg2mm(messageHandler.getTargetEyeWindowSize());
			double targetX = getRenderer().deg2mm(targetLocation.getX());
			double targetY = getRenderer().deg2mm(targetLocation.getY());
			
			GLUtil.drawCircle(getCircle(), targetEyeWindowSize, false, targetX, targetY, 0);
			GLUtil.drawSquare(getSquare(), targetIndicatorSize, true, targetX, targetY, 0);
		}
	}
	
	public void setSaccadeMessageHandler(SaccadeExperimentMessageHandler messageHandler) {
		this.messageHandler = messageHandler;
	}

}