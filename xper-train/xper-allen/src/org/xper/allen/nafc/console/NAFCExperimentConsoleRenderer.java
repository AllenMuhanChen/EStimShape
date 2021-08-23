package org.xper.allen.nafc.console;

import org.xper.Dependency;
import org.xper.allen.nafc.message.NAFCExperimentMessageHandler;
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
			int n = choicesLocations.length;
			
			double[] targetEyeWindowSize = new double[n];
			double[] targetX = new double[n];
			double[] targetY = new double[n];
			
			for (int i = 0; i < n; i++) {
			targetEyeWindowSize[i] = renderer.deg2mm(messageHandler.getTargetEyeWindowSize()[i]);
			targetX[i] = renderer.deg2mm(choicesLocations[i].getX());
			targetY[i] = renderer.deg2mm(choicesLocations[i].getY());
			GLUtil.drawCircle(circle, targetEyeWindowSize[i], false, targetX[i], targetY[i], 0);
			GLUtil.drawSquare(square, targetIndicatorSize, true, targetX[i], targetY[i], 0);
			}		
		}
	}
	
	public void setTwoACMessageHandler(NAFCExperimentMessageHandler messageHandler) {
		this.messageHandler = messageHandler;
	}
}
