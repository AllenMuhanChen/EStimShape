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
			double targetEyeWindowSize = renderer.deg2mm(messageHandler.getTargetEyeWindowSize());
			double targetX = renderer.deg2mm(targetLocation.getX());
			double targetY = renderer.deg2mm(targetLocation.getY());
			
			GLUtil.drawCircle(circle, targetEyeWindowSize, false, targetX, targetY, 0);
			GLUtil.drawSquare(square, targetIndicatorSize, true, targetX, targetY, 0);
		}
	}
	
	public void setSaccadeMessageHandler(SaccadeExperimentMessageHandler messageHandler) {
		this.messageHandler = messageHandler;
	}

}