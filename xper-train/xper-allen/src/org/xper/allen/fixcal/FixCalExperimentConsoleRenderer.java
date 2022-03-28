package org.xper.allen.fixcal;

import java.awt.Rectangle;

import org.xper.classic.TrialExperimentConsoleRenderer;
import org.xper.drawing.Context;
import org.xper.drawing.GLUtil;
import org.xper.drawing.object.Square;

public class FixCalExperimentConsoleRenderer extends TrialExperimentConsoleRenderer {
	public void drawCanvas(Context context, String devId) {
		getBlankScreen().draw(null);
		drawScreenCenter();
		if (getMessageHandler().isInTrial()) {
			drawFixation();
			drawEyeDevice(devId);
		}
	}
	
	protected void drawScreenCenter() {
		GLUtil.drawCircle(getCircle(), 5, true, 0, 0, 0);
	}
}
