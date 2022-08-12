package org.xper.classic;

import java.util.Map;

import org.xper.Dependency;
import org.xper.classic.vo.TrialContext;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.Drawable;
import org.xper.drawing.GLUtil;
import org.xper.drawing.object.Circle;
import org.xper.drawing.object.Square;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.eye.vo.EyeDeviceReading;
import org.xper.eye.vo.EyeWindow;

public class TrialExperimentConsoleRenderer {
	@Dependency
	protected AbstractRenderer renderer;
	@Dependency
	Drawable fixation;
	@Dependency
	Drawable blankScreen;
	@Dependency
	Circle circle;
	@Dependency
	Square square;
	
	double eyeIndicatorSize = 2.5;
	double voltageIndicatorSize = 5;
	double voltageMin = -10.0;
	double voltageMax = 10.0;
	
	@Dependency
	protected TrialExperimentMessageHandler messageHandler;
	
	public void drawCanvas(Context context, String devId) {
		blankScreen.draw(null);
		if (messageHandler.isInTrial()) {
			drawFixation();
			drawEyeDevice(devId);
		}
	}
	
	void drawEyeDevice(String devId) {
		drawEyeWindow();
		drawEyeDeviceReading(devId);
	}
	
	void drawEyeWindow() {
		EyeWindow window = messageHandler.getEyeWindow();
		Coordinates2D eyeWindowCenter = window.getCenter();
		double eyeWindowCenterX = renderer.deg2mm(eyeWindowCenter.getX());
		double eyeWindowCenterY = renderer.deg2mm(eyeWindowCenter.getY());
		double eyeWindowSize = renderer.deg2mm(window.getSize());

		GLUtil.drawCircle(circle, eyeWindowSize, false, eyeWindowCenterX, eyeWindowCenterY, 0.0);
	}
	
	void drawEyeDeviceReading(String devId) {
		for (Map.Entry<String, EyeDeviceReading> ent : messageHandler
				.getEyeDeviceReadingEntries()) {
			
			String id = ent.getKey();
			if (!id.equalsIgnoreCase(devId)) {
				continue;
			}
			
			EyeDeviceReading reading = ent.getValue();

			// Eye Position
			Coordinates2D eyeDegree = reading.getDegree();
			
			boolean solid = false;
			if (messageHandler.isEyeIn()) {
				solid = true;
			} 
			GLUtil.drawCircle(circle, eyeIndicatorSize, solid, renderer.deg2mm(eyeDegree.getX()), renderer
					.deg2mm(eyeDegree.getY()), 0.0);

			// Eye Voltage
			Coordinates2D eyeVolt = reading.getVolt();
			double xmin = renderer.getXmin();
			double xmax = renderer.getXmax();

			double ymin = renderer.getYmin();
			double ymax = renderer.getYmax();

			float xmm = (float) ((eyeVolt.getX() - voltageMin) * (xmax - xmin)
					/ (voltageMax - voltageMin) + xmin);
			float ymm = (float) ((eyeVolt.getY() - voltageMin) * (ymax - ymin)
					/ (voltageMax - voltageMin) + ymin);

			GLUtil.drawSquare(square, voltageIndicatorSize, true, xmm, ymm, 0);
		}
	}
	
	void drawFixation() {
		if (messageHandler.isFixationOn()) {
			TrialContext context = new TrialContext();
			context.setRenderer(renderer);
			fixation.draw(context);
		}
	}
	
	public TrialExperimentMessageHandler getMessageHandler() {
		return messageHandler;
	}

	public void setMessageHandler(TrialExperimentMessageHandler messageHandler) {
		this.messageHandler = messageHandler;
	}

	public Circle getCircle() {
		return circle;
	}

	public void setCircle(Circle circle) {
		this.circle = circle;
	}
	
	public Square getSquare() {
		return square;
	}

	public void setSquare(Square square) {
		this.square = square;
	}
	
	public Drawable getFixation() {
		return fixation;
	}

	public void setFixation(Drawable fixation) {
		this.fixation = fixation;
	}
	
	public Drawable getBlankScreen() {
		return blankScreen;
	}

	public void setBlankScreen(Drawable blankScreen) {
		this.blankScreen = blankScreen;
	}
	
	public AbstractRenderer getRenderer() {
		return renderer;
	}

	public void setRenderer(AbstractRenderer renderer) {
		this.renderer = renderer;
	}
}
