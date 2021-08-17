package org.xper.allen.nafc.console;

import org.xper.Dependency;
import org.xper.allen.saccade.console.SaccadeExperimentMessageHandler;
import org.xper.classic.TrialExperimentConsoleRenderer;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.GLUtil;

public class NAFCExperimentConsoleRenderer extends TrialExperimentConsoleRenderer{
	@Dependency
	NAFCExperimentMessageHandler messageHandler;
	
	double targetIndicatorSize = 2.5;
	int invert;
	
	public void drawCanvas(Context context, String devId) {
		super.drawCanvas(context, devId);
		if(getMessageHandler().isInTrial()) {
			drawChoices();
		}	
		
	}
	
	void drawChoices() {
		if(messageHandler.isChoicesOn()) {
			Coordinates2D[] choicesLocations = messageHandler.getTargetPosition();
			double[] targetEyeWindowSize = {renderer.deg2mm(messageHandler.getTargetEyeWindowSize()[0]), renderer.deg2mm(messageHandler.getTargetEyeWindowSize()[1])};
			double[] targetX = {renderer.deg2mm(choicesLocations[0].getX()), renderer.deg2mm(choicesLocations[1].getX())};
			double[] targetY = {renderer.deg2mm(choicesLocations[0].getY()), renderer.deg2mm(choicesLocations[1].getY())};
			
			GLUtil.drawCircle(circle, targetEyeWindowSize[0], false, targetX[0], targetY[0], 0);
			GLUtil.drawCircle(circle, targetEyeWindowSize[1], false, targetX[1], targetY[1], 0);
			GLUtil.drawSquare(square, targetIndicatorSize, true, targetX[0], targetY[0], 0);
			GLUtil.drawSquare(square, targetIndicatorSize, true, targetX[1], targetY[1], 0);
		}
	}
	
	public void setTwoACMessageHandler(NAFCExperimentMessageHandler messageHandler) {
		this.messageHandler = messageHandler;
	}
}
