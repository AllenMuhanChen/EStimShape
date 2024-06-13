package org.xper.allen.nafc.console;

import org.xper.Dependency;
import org.xper.allen.nafc.message.NAFCExperimentMessageHandler;
import org.xper.allen.saccade.console.SaccadeExperimentMessageHandler;
import org.xper.classic.TrialExperimentConsoleRenderer;
import org.xper.classic.vo.TrialContext;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.GLUtil;

/**
 * Pretty much responsible for everything that is drawn in the black window of the NAFCConsole

 */
public class NAFCExperimentConsoleRenderer extends TrialExperimentConsoleRenderer{
	@Dependency
	NAFCExperimentMessageHandler messageHandler;

	double targetIndicatorSize = 2.5;

	public NAFCExperimentConsoleRenderer() {
		super();
		super.setMessageHandler(messageHandler);
	}

	public void drawCanvas(Context context, String devId) {
		getBlankScreen().draw(null);

		if(messageHandler.isInTrial()) {
			drawEyeDeviceReading(devId);
			drawChoices();
		}
		if(messageHandler.isSampleOn()){
			drawFixation();
			drawEyeWindow();
		}
		if(messageHandler.isFixationOn()){
			drawEyeDevice(devId);
			drawFixation();
		}

	}

	protected void drawFixation() {
		if (messageHandler.isFixationOn() || messageHandler.isSampleOn()) {
			TrialContext context = new TrialContext();
			context.setRenderer(getRenderer());
			getFixation().draw(context);
		}
	}

	void drawChoices() {
			if(messageHandler.isChoicesOn()) {
				try {
					Coordinates2D[] choicesLocations = messageHandler.getTargetPosition();

					int n = choicesLocations.length;

					double[] targetEyeWindowSize = new double[n];
					double[] targetX = new double[n];
					double[] targetY = new double[n];

					for (int i = 0; i < n; i++) {
						targetEyeWindowSize[i] = getRenderer().deg2mm(messageHandler.getTargetEyeWindowSize()[i]);
						targetX[i] = getRenderer().deg2mm(choicesLocations[i].getX());
						targetY[i] = getRenderer().deg2mm(choicesLocations[i].getY());
						GLUtil.drawCircle(getCircle(), targetEyeWindowSize[i], false, targetX[i], targetY[i], 0);
						GLUtil.drawSquare(getSquare(), targetIndicatorSize, true, targetX[i], targetY[i], 0);
					}
				}
				catch (NullPointerException e) {
					System.out.println("Null Pointer Exception in NAFCExperimentConsoleRenderer.drawChoices(). Skipping this drawing. ");
				}
			}
		}


	/**
	 * This is an appropiate way to give the superclass access to a new variable which the superclass does not declare
	 * @param messageHandler
	 */
	public void setNAFCExperimentMessageHandler(NAFCExperimentMessageHandler messageHandler) {
		this.messageHandler = messageHandler;
		super.setMessageHandler(messageHandler);
	}
}