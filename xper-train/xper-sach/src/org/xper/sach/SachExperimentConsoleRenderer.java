package org.xper.sach;


import org.xper.classic.TrialExperimentConsoleRenderer;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.sach.util.SachExperimentUtil;

public class SachExperimentConsoleRenderer extends
		TrialExperimentConsoleRenderer {
	
	@Override
	public void drawCanvas(Context context, String devId) {
		super.drawCanvas(context, devId);
		if (getMessageHandler() instanceof SachExperimentMessageHandler) {
			SachExperimentMessageHandler r = (SachExperimentMessageHandler) getMessageHandler();
			if (r.isTargetOn()) {
				RGBColor targetColor = new RGBColor(1f, 1f, 0f);
				Coordinates2D pos = r.getTargetPosition();
				double eyeWinSize = r.getTargetEyeWindowSize();
				if (pos != null) {
					SachExperimentUtil.drawTargetEyeWindow(getRenderer(), pos, eyeWinSize, targetColor);
				}
			}
		}
	}
}
